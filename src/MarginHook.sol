// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.26;

// V4 core
import {BaseHook} from "v4-periphery/src/base/hooks/BaseHook.sol";
import {PoolKey} from "v4-core/types/PoolKey.sol";
import {PoolId, PoolIdLibrary} from "v4-core/types/PoolId.sol";
import {BalanceDelta} from "v4-core/types/BalanceDelta.sol";
import {BeforeSwapDelta, toBeforeSwapDelta} from "v4-core/types/BeforeSwapDelta.sol";
import {Currency, CurrencyLibrary} from "v4-core/types/Currency.sol";
import {Hooks} from "v4-core/libraries/Hooks.sol";
import {IPoolManager} from "v4-core/interfaces/IPoolManager.sol";
import {SafeCast} from "v4-core/libraries/SafeCast.sol";
// Solmate
import {ERC20} from "solmate/src/Tokens/ERC20.sol";
// Local
import {CurrencySettleTake} from "./libraries/CurrencySettleTake.sol";
import {Math} from "./libraries/Math.sol";
import {UnsafeMath} from "./libraries/UnsafeMath.sol";
import {IMarginHookFactory} from "./interfaces/IMarginHookFactory.sol";

contract MarginHook is BaseHook, ERC20 {
    using UnsafeMath for uint256;
    using SafeCast for uint256;
    using CurrencySettleTake for Currency;
    using CurrencyLibrary for Currency;

    error BalanceOverflow();
    error InvalidInitialization();
    error InsufficientLiquidityMinted();
    error InsufficientLiquidityBurnt();
    error AddLiquidityDirectToHook();
    error IncorrectSwapAmount();

    event Mint(address indexed sender, uint256 amount0, uint256 amount1);
    event Burn(address indexed sender, uint256 amount0, uint256 amount1, address indexed to);
    event Swap(uint256 amountIn, uint256 amountOut);
    event Sync(uint128 reserves0, uint128 reserves1);

    uint256 public constant MINIMUM_LIQUIDITY = 10 ** 3;
    uint24 public initialLTV = 5000;
    uint24 public liquidationLTV = 9000;
    Currency public immutable currency0;
    Currency public immutable currency1;
    address public immutable factory;

    uint128 private reserves0;
    uint128 private reserves1;

    constructor(IPoolManager _manager, string memory _name, string memory _symbol)
        BaseHook(_manager)
        ERC20(_name, _symbol, 18)
    {
        (currency0, currency1, poolManager) = IMarginHookFactory(msg.sender).parameters();
        factory = msg.sender;
    }

    function getReserves() public view returns (uint128 _reserves0, uint128 _reserves1) {
        _reserves0 = reserves0;
        _reserves1 = reserves1;
    }

    // ******************** V2 FUNCTIONS ********************

    // this low-level function should be called from a contract which performs important safety checks
    function mint(address to) external returns (uint256 liquidity) {
        (uint128 _reserves0, uint128 _reserves1) = getReserves();
        uint256 _totalSupply = totalSupply;

        // The caller has already minted 6909s on the PoolManager to this address
        uint256 balance0 = poolManager.balanceOf(address(this), CurrencyLibrary.toId(currency0));
        uint256 balance1 = poolManager.balanceOf(address(this), CurrencyLibrary.toId(currency1));
        uint256 amount0 = balance0 - _reserves0;
        uint256 amount1 = balance1 - _reserves1;

        if (_totalSupply == 0) {
            liquidity = Math.sqrt(amount0 * amount1) - MINIMUM_LIQUIDITY;
            _mint(address(0), MINIMUM_LIQUIDITY); // permanently lock the first MINIMUM_LIQUIDITY tokens
        } else {
            liquidity =
                Math.min((amount0 * _totalSupply).unsafeDiv(_reserves0), (amount1 * _totalSupply).unsafeDiv(_reserves1));
        }
        if (liquidity == 0) revert InsufficientLiquidityMinted();
        _mint(to, liquidity);

        _update(balance0, balance1);
        emit Mint(msg.sender, amount0, amount1);
    }

    // this low-level function should be called from a contract which performs important safety checks
    function burn(address to) external returns (uint256 amount0, uint256 amount1) {
        uint256 balance0 = poolManager.balanceOf(address(this), CurrencyLibrary.toId(currency0));
        uint256 balance1 = poolManager.balanceOf(address(this), CurrencyLibrary.toId(currency1));
        uint256 liquidity = balanceOf[address(this)];

        amount0 = (liquidity * balance0).unsafeDiv(totalSupply); // using balances ensures pro-rata distribution
        amount1 = (liquidity * balance1).unsafeDiv(totalSupply); // using balances ensures pro-rata distribution
        if (amount0 == 0 || amount1 == 0) revert InsufficientLiquidityBurnt();

        _burn(address(this), liquidity);

        _burn6909s(amount0, amount1, to);
        balance0 -= amount0;
        balance1 -= amount1;

        _update(balance0, balance1);
        emit Burn(msg.sender, amount0, amount1, to);
    }

    // force balances to match reserves
    function skim(address to) external {
        currency0.transfer(to, currency0.balanceOf(address(this)) - reserves0);
        currency1.transfer(to, currency1.balanceOf(address(this)) - reserves1);
    }

    // force reserves to match balances
    function sync() external {
        _update(currency0.balanceOf(address(this)), currency1.balanceOf(address(this)));
    }

    // ******************** MARGIN FUNCTIONS ********************

    function borrow(address to, uint256 marginSell, uint24 leverage, address borrowToken)
        external
        payable
        returns (uint256 borrowAmount)
    {
        require(currency0 == Currency.wrap(borrowToken) || currency1 == Currency.wrap(borrowToken), "borrow token err");
        bool zeroForOne = currency0 == Currency.wrap(borrowToken);
        uint256 borrowReserves = zeroForOne ? reserves0 : reserves1;
        uint256 total = marginSell * leverage * initialLTV / (2 * 10 ** 4);
        borrowAmount = _getAmountOut(zeroForOne, total);
        require(borrowReserves > borrowAmount, "token not enough");
        total = _getAmountIn(zeroForOne, borrowAmount);
    }

    // ******************** HOOK FUNCTIONS ********************

    function beforeInitialize(address sender, PoolKey calldata key, uint160) external view override returns (bytes4) {
        if (
            sender != factory || key.fee != 0 || key.tickSpacing != 1
                || Currency.unwrap(key.currency0) != Currency.unwrap(currency0)
                || Currency.unwrap(key.currency1) != Currency.unwrap(currency1)
        ) revert InvalidInitialization();
        return BaseHook.beforeInitialize.selector;
    }

    /// @dev Facilitate a custom curve via beforeSwap + return delta
    /// @dev input tokens are taken from the PoolManager, creating a debt paid by the swapper
    /// @dev output takens are transferred from the hook to the PoolManager, creating a credit claimed by the swapper
    function beforeSwap(address, PoolKey calldata key, IPoolManager.SwapParams calldata params, bytes calldata)
        external
        override
        returns (bytes4, BeforeSwapDelta, uint24)
    {
        bool exactInput = params.amountSpecified < 0;
        (Currency specified, Currency unspecified) =
            (params.zeroForOne == exactInput) ? (key.currency0, key.currency1) : (key.currency1, key.currency0);

        uint256 specifiedAmount = exactInput ? uint256(-params.amountSpecified) : uint256(params.amountSpecified);
        uint256 unspecifiedAmount;
        BeforeSwapDelta returnDelta;
        if (exactInput) {
            // in exact-input swaps, the specified token is a debt that gets paid down by the swapper
            // the unspecified token is credited to the PoolManager, that is claimed by the swapper
            unspecifiedAmount = _getAmountOut(params.zeroForOne, specifiedAmount);
            specified.take(poolManager, address(this), specifiedAmount, true);
            unspecified.settle(poolManager, address(this), unspecifiedAmount, true);

            returnDelta = toBeforeSwapDelta(specifiedAmount.toInt128(), -unspecifiedAmount.toInt128());
        } else {
            // exactOutput
            // in exact-output swaps, the unspecified token is a debt that gets paid down by the swapper
            // the specified token is credited to the PoolManager, that is claimed by the swapper
            unspecifiedAmount = _getAmountIn(params.zeroForOne, specifiedAmount);
            unspecified.take(poolManager, address(this), unspecifiedAmount, true);
            specified.settle(poolManager, address(this), specifiedAmount, true);

            returnDelta = toBeforeSwapDelta(-specifiedAmount.toInt128(), unspecifiedAmount.toInt128());
        }

        return (BaseHook.beforeSwap.selector, returnDelta, 0);
    }

    /// @notice No liquidity will be managed by v4 PoolManager
    function beforeAddLiquidity(address, PoolKey calldata, IPoolManager.ModifyLiquidityParams calldata, bytes calldata)
        external
        pure
        override
        returns (bytes4)
    {
        revert("No v4 Liquidity allowed");
    }

    function getHookPermissions() public pure override returns (Hooks.Permissions memory) {
        return Hooks.Permissions({
            beforeInitialize: false,
            afterInitialize: false,
            beforeAddLiquidity: true, // -- disable v4 liquidity with a revert -- //
            beforeRemoveLiquidity: false,
            afterAddLiquidity: false,
            afterRemoveLiquidity: false,
            beforeSwap: true, // -- Custom Curve Handler --  //
            afterSwap: false,
            beforeDonate: false,
            afterDonate: false,
            beforeSwapReturnDelta: true, // -- Enables Custom Curves --  //
            afterSwapReturnDelta: false,
            afterAddLiquidityReturnDelta: false,
            afterRemoveLiquidityReturnDelta: false
        });
    }

    // ******************** INTERNAL FUNCTIONS ********************

    function _update(uint256 balance0, uint256 balance1) private {
        if (balance0 > type(uint128).max || balance1 > type(uint128).max) revert BalanceOverflow();
        reserves0 = uint128(balance0);
        reserves1 = uint128(balance1);
        emit Sync(reserves0, reserves1);
    }

    // given an input amount of an asset and pair reserves, returns the maximum output amount of the other asset
    function _getAmountOut(bool zeroForOne, uint256 amountIn) internal view returns (uint256 amountOut) {
        require(amountIn > 0, "UniswapV2Library: INSUFFICIENT_INPUT_AMOUNT");

        (uint256 reservesIn, uint256 reservesOut) = zeroForOne ? (reserves0, reserves1) : (reserves1, reserves0);
        require(reserves0 > 0 && reserves1 > 0, "UniswapV2Library: INSUFFICIENT_LIQUIDITY");

        uint256 amountInWithFee = amountIn * 997;
        uint256 numerator = amountInWithFee * reservesOut;
        uint256 denominator = (reservesIn * 1000) + amountInWithFee;
        amountOut = numerator / denominator;
    }

    // given an output amount of an asset and pair reserves, returns a required input amount of the other asset
    function _getAmountIn(bool zeroForOne, uint256 amountOut) internal view returns (uint256 amountIn) {
        require(amountOut > 0, "UniswapV2Library: INSUFFICIENT_OUTPUT_AMOUNT");

        (uint256 reservesIn, uint256 reservesOut) = zeroForOne ? (reserves0, reserves1) : (reserves1, reserves0);
        require(reservesIn > 0 && reservesOut > 0, "UniswapV2Library: INSUFFICIENT_LIQUIDITY");

        uint256 numerator = reservesIn * amountOut * 1000;
        uint256 denominator = (reservesOut - amountOut) * 997;
        amountIn = (numerator / denominator) + 1;
    }

    function _getInputOutput(PoolKey calldata key, bool zeroForOne)
        internal
        pure
        returns (Currency input, Currency output)
    {
        (input, output) = zeroForOne ? (key.currency0, key.currency1) : (key.currency1, key.currency0);
    }

    // ******************** 6909 BURNING ********************

    function _burn6909s(uint256 amount0, uint256 amount1, address to) internal {
        poolManager.unlock(abi.encodeCall(this.handleBurn6909s, (amount0, amount1, to)));
    }

    function handleBurn6909s(uint256 amount0, uint256 amount1, address to) external selfOnly returns (bytes memory) {
        poolManager.burn(address(this), CurrencyLibrary.toId(currency0), amount0);
        poolManager.burn(address(this), CurrencyLibrary.toId(currency1), amount1);
        currency0.take(poolManager, to, amount0, false);
        currency1.take(poolManager, to, amount1, false);

        return abi.encode(amount0, amount1);
    }
}
