// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.26;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {IERC20Minimal} from "v4-core/interfaces/external/IERC20Minimal.sol";
import {Owned} from "solmate/src/auth/Owned.sol";
import {Currency, CurrencyLibrary} from "v4-core/types/Currency.sol";
import {IERC20Minimal} from "v4-core/interfaces/external/IERC20Minimal.sol";
import {PoolId} from "v4-core/types/PoolId.sol";
// Local
import {CurrencyUtils} from "./libraries/CurrencyUtils.sol";
import {IMarginPositionManager} from "./interfaces/IMarginPositionManager.sol";
import {IMarginHookManager} from "./interfaces/IMarginHookManager.sol";
import {IMarginOracleReader} from "./interfaces/IMarginOracleReader.sol";
import {MarginPosition} from "./types/MarginPosition.sol";
import {HookStatus} from "./types/HookStatus.sol";
import {MarginParams, ReleaseParams} from "./types/MarginParams.sol";
import {Math} from "./libraries/Math.sol";
import {UQ112x112} from "./libraries/UQ112x112.sol";

import {console} from "forge-std/console.sol";

contract MarginPositionManager is IMarginPositionManager, ERC721, Owned {
    using CurrencyUtils for Currency;
    using CurrencyLibrary for Currency;
    using UQ112x112 for uint224;

    error PairNotExists();
    error Liquidated();
    error InsufficientBorrowReceived();

    event Mint(PoolId indexed poolId, address indexed sender, address indexed to, uint256 positionId);
    event Burn(PoolId indexed poolId, address indexed sender, uint256 positionId);
    event Margin(
        PoolId indexed poolId,
        address indexed owner,
        uint256 positionId,
        uint256 marginAmount,
        uint256 marginTotal,
        uint256 borrowAmount,
        bool marginForOne
    );
    event Repay(PoolId indexed poolId, address indexed sender, uint256 positionId, uint256 repayAmount);
    event Close(
        PoolId indexed poolId, address indexed sender, uint256 positionId, uint256 releaseAmount, uint256 repayAmount
    );

    uint256 public constant ONE_MILLION = 10 ** 6;
    uint256 private _nextId = 1;

    IMarginHookManager private hook;
    address public marginOracle;

    mapping(uint256 => MarginPosition) private _positions;
    mapping(address => uint256) private _hookPositions;
    mapping(PoolId => mapping(bool => mapping(address => uint256))) private _borrowPositions;

    constructor(address initialOwner) ERC721("LIKWIDMarginPositionManager", "LMPM") Owned(initialOwner) {}

    function _burnPosition(uint256 positionId) internal {
        // _burn(positionId);
        MarginPosition memory _position = _positions[positionId];
        delete _borrowPositions[_position.poolId][_position.marginForOne][ownerOf(positionId)];
        delete _positions[positionId];
        emit Burn(_position.poolId, msg.sender, positionId);
    }

    modifier ensure(uint256 deadline) {
        require(deadline >= block.timestamp, "EXPIRED");
        _;
    }

    function transferNative(address to, uint256 amount) internal {
        (bool success,) = to.call{value: amount}("");
        require(success, "Transfer failed.");
    }

    function setHook(address _hook) external onlyOwner {
        hook = IMarginHookManager(_hook);
    }

    function getHook() external view returns (address _hook) {
        _hook = address(hook);
    }

    function setMarginOracle(address _oracle) external onlyOwner {
        marginOracle = _oracle;
    }

    function getPosition(uint256 positionId) public view returns (MarginPosition memory _position) {
        _position = _positions[positionId];
        if (_position.rateCumulativeLast > 0) {
            uint256 rateLast = hook.getBorrowRateCumulativeLast(_position.poolId, _position.marginForOne);
            _position.borrowAmount = _position.borrowAmount * rateLast / _position.rateCumulativeLast;
        }
    }

    function getPositionId(PoolId poolId, bool marginForOne, address owner)
        external
        view
        returns (uint256 _positionId)
    {
        _positionId = _borrowPositions[poolId][marginForOne][owner];
    }

    function checkAmount(Currency currency, address payer, address recipient, uint256 amount)
        internal
        returns (bool valid)
    {
        if (currency.isAddressZero()) {
            valid = msg.value >= amount;
        } else {
            if (payer != address(this)) {
                valid = IERC20Minimal(Currency.unwrap(currency)).allowance(payer, recipient) >= amount;
            } else {
                valid = IERC20Minimal(Currency.unwrap(currency)).balanceOf(address(this)) >= amount;
            }
        }
    }

    function margin(MarginParams memory params) external payable ensure(params.deadline) returns (uint256, uint256) {
        HookStatus memory _status = hook.getStatus(params.poolId);
        Currency marginToken = params.marginForOne ? _status.key.currency1 : _status.key.currency0;
        require(checkAmount(marginToken, msg.sender, address(this), params.marginAmount), "INSUFFICIENT_AMOUNT");
        bool success = marginToken.transfer(msg.sender, address(this), params.marginAmount);
        require(success, "MARGIN_ERR");
        uint256 positionId = _borrowPositions[params.poolId][params.marginForOne][params.recipient];
        params = hook.margin(params);
        uint256 rateLast = hook.getBorrowRateCumulativeLast(params.poolId, params.marginForOne);
        if (params.borrowAmount < params.borrowMinAmount) revert InsufficientBorrowReceived();
        if (positionId == 0) {
            _mint(params.recipient, (positionId = _nextId++));
            emit Mint(params.poolId, msg.sender, params.recipient, positionId);
            _positions[positionId] = MarginPosition({
                poolId: params.poolId,
                marginForOne: params.marginForOne,
                marginAmount: params.marginAmount,
                marginTotal: params.marginTotal,
                borrowAmount: params.borrowAmount,
                rateCumulativeLast: rateLast
            });
            _borrowPositions[params.poolId][params.marginForOne][params.recipient] = positionId;
        } else {
            MarginPosition storage _position = _positions[positionId];
            (bool liquidated,) = checkLiquidate(_position);
            require(!liquidated, "liquidated");
            _position.marginAmount += params.marginAmount;
            _position.marginTotal += params.marginTotal;
            _position.borrowAmount =
                _position.borrowAmount * rateLast / _position.rateCumulativeLast + params.borrowAmount;
            _position.rateCumulativeLast = rateLast;
        }
        emit Margin(
            params.poolId,
            params.recipient,
            positionId,
            params.marginAmount,
            params.marginTotal,
            params.borrowAmount,
            params.marginForOne
        );
        return (positionId, params.borrowAmount);
    }

    function release(uint256 positionId, Currency marginToken, uint256 repayAmount, uint256 borrowAmount) internal {
        MarginPosition storage _position = _positions[positionId];
        (bool liquidated,) = checkLiquidate(_position);
        require(!liquidated, "liquidated");
        // update position
        uint256 releaseMargin = _position.marginAmount * repayAmount / borrowAmount;
        uint256 releaseTotal = _position.marginTotal * repayAmount / borrowAmount;
        _position.marginAmount -= releaseMargin;
        _position.marginTotal -= releaseTotal;
        _position.borrowAmount = borrowAmount - repayAmount;
        bool success = marginToken.transfer(address(this), msg.sender, releaseMargin + releaseTotal);
        require(success, "RELEASE_TRANSFER_ERR");
        if (_position.borrowAmount == 0) {
            _burnPosition(positionId);
        }
    }

    function repay(uint256 positionId, uint256 repayAmount, uint256 deadline) external payable ensure(deadline) {
        require(ownerOf(positionId) == msg.sender, "AUTH_ERROR");
        MarginPosition memory _position = getPosition(positionId);
        HookStatus memory _status = hook.getStatus(_position.poolId);
        (Currency borrowToken, Currency marginToken) = _position.marginForOne
            ? (_status.key.currency0, _status.key.currency1)
            : (_status.key.currency1, _status.key.currency0);
        require(checkAmount(borrowToken, msg.sender, address(hook), repayAmount), "INSUFFICIENT_AMOUNT");
        if (repayAmount > _position.borrowAmount) {
            repayAmount = _position.borrowAmount;
        }
        ReleaseParams memory params = ReleaseParams({
            poolId: _position.poolId,
            marginForOne: _position.marginForOne,
            payer: msg.sender,
            borrowAmount: _position.borrowAmount,
            repayAmount: repayAmount,
            releaseAmount: 0,
            deadline: deadline
        });
        uint256 sendValue = Math.min(repayAmount, msg.value);
        hook.release{value: sendValue}(params);
        release(positionId, marginToken, repayAmount, _position.borrowAmount);
        if (msg.value > sendValue) {
            transferNative(msg.sender, msg.value - sendValue);
        }
        emit Repay(_position.poolId, msg.sender, positionId, repayAmount);
    }

    function estimatePNL(uint256 positionId, uint256 repayMillionth) external view returns (int256 pnlMinAmount) {
        MarginPosition memory _position = getPosition(positionId);
        uint256 repayAmount = _position.borrowAmount * repayMillionth / ONE_MILLION;
        uint256 releaseAmount = hook.getAmountOut(_position.poolId, _position.marginForOne, repayAmount);
        uint256 sendValue = (_position.marginAmount + _position.marginTotal) * repayMillionth / ONE_MILLION;
        pnlMinAmount = int256(sendValue) - int256(releaseAmount);
    }

    function close(uint256 positionId, uint256 releaseMargin, uint256 releaseTotal, uint256 borrowAmount) internal {
        // update position
        MarginPosition storage sPosition = _positions[positionId];
        sPosition.marginAmount -= releaseMargin;
        sPosition.marginTotal -= releaseTotal;
        sPosition.borrowAmount = borrowAmount;
        if (sPosition.borrowAmount == 0) {
            _burnPosition(positionId);
        }
    }

    function close(uint256 positionId, uint256 repayMillionth, int256 pnlMinAmount, uint256 deadline)
        external
        payable
        ensure(deadline)
    {
        require(ownerOf(positionId) == msg.sender, "AUTH_ERROR");
        require(repayMillionth <= ONE_MILLION, "MILLIONTH_ERROR");
        MarginPosition memory _position = getPosition(positionId);
        HookStatus memory _status = hook.getStatus(_position.poolId);
        Currency marginToken = _position.marginForOne ? _status.key.currency1 : _status.key.currency0;
        ReleaseParams memory params = ReleaseParams({
            poolId: _position.poolId,
            marginForOne: _position.marginForOne,
            payer: address(this),
            borrowAmount: _position.borrowAmount,
            repayAmount: 0,
            releaseAmount: 0,
            deadline: deadline
        });
        params.repayAmount = _position.borrowAmount * repayMillionth / ONE_MILLION;
        params.releaseAmount = hook.getAmountOut(_position.poolId, _position.marginForOne, params.repayAmount);
        uint256 releaseMargin = _position.marginAmount * repayMillionth / ONE_MILLION;
        uint256 releaseTotal = _position.marginTotal * repayMillionth / ONE_MILLION;
        uint256 userMarginAmount;
        if (releaseMargin + releaseTotal >= params.releaseAmount) {
            require(
                pnlMinAmount < int256(releaseMargin + releaseTotal) - int256(params.releaseAmount),
                "InsufficientOutputReceived"
            );
            marginToken.transfer(address(this), msg.sender, releaseMargin + releaseTotal - params.releaseAmount);
        } else {
            uint256 marginAmount = _position.marginAmount * (ONE_MILLION - repayMillionth) / ONE_MILLION;
            if (releaseMargin + releaseTotal + marginAmount >= params.releaseAmount) {
                require(
                    pnlMinAmount > int256(releaseMargin + releaseTotal) - int256(params.releaseAmount),
                    "InsufficientOutputReceived"
                );
                userMarginAmount = params.releaseAmount - (releaseMargin + releaseTotal);
            } else {
                // liquidated
                revert Liquidated();
            }
        }
        if (marginToken == CurrencyLibrary.ADDRESS_ZERO) {
            hook.release{value: params.releaseAmount}(params);
        } else {
            bool success = marginToken.approve(address(hook), params.releaseAmount);
            require(success, "APPROVE_ERR");
            hook.release(params);
        }
        close(positionId, releaseMargin + userMarginAmount, releaseTotal, _position.borrowAmount - params.repayAmount);
        emit Close(_position.poolId, msg.sender, positionId, params.releaseAmount, params.repayAmount);
    }

    function checkLiquidate(MarginPosition memory _position)
        private
        view
        returns (bool liquidated, uint256 amountNeed)
    {
        if (_position.rateCumulativeLast > 0) {
            uint256 rateLast = hook.getBorrowRateCumulativeLast(_position.poolId, _position.marginForOne);
            uint256 borrowAmount = _position.borrowAmount * rateLast / _position.rateCumulativeLast;
            if (marginOracle == address(0)) {
                (uint256 reserve0, uint256 reserve1) = hook.getReserves(_position.poolId);
                (uint256 reserveBorrow, uint256 reserveMargin) =
                    _position.marginForOne ? (reserve0, reserve1) : (reserve1, reserve0);
                amountNeed = reserveMargin * borrowAmount / reserveBorrow;
            } else {
                (uint224 reserves,) = IMarginOracleReader(marginOracle).observeNow(_position.poolId, address(hook));
                (uint256 reserveBorrow, uint256 reserveMargin) = _position.marginForOne
                    ? (reserves.getReverse0(), reserves.getReverse1())
                    : (reserves.getReverse1(), reserves.getReverse0());
                console.log("reserveBorrow:%s,reserveMargin:%s", reserveBorrow, reserveMargin);
                amountNeed = reserveMargin * borrowAmount / reserveBorrow;
            }

            (, uint24 _liquidationLTV) = hook.ltvParameters(_position.poolId);
            liquidated = amountNeed > _position.marginAmount * _liquidationLTV / ONE_MILLION + _position.marginTotal;
        }
    }

    function checkLiquidate(uint256 positionId) public view returns (bool liquidated, uint256 releaseAmount) {
        MarginPosition memory _position = _positions[positionId];
        uint256 amountNeed;
        (liquidated, amountNeed) = checkLiquidate(_position);
        releaseAmount = Math.min(amountNeed, _position.marginAmount + _position.marginTotal);
    }

    function liquidateBurn(uint256 positionId) external returns (uint256 profit) {
        (bool liquidated, uint256 releaseAmount) = checkLiquidate(positionId);
        if (!liquidated) {
            return profit;
        }
        MarginPosition memory _position = _positions[positionId];
        HookStatus memory _status = hook.getStatus(_position.poolId);
        uint256 liquidateValue = 0;
        Currency marginToken = _position.marginForOne ? _status.key.currency1 : _status.key.currency0;
        if (marginToken == CurrencyLibrary.ADDRESS_ZERO) {
            liquidateValue = releaseAmount;
        } else {
            bool success = marginToken.approve(address(hook), releaseAmount);
            require(success, "APPROVE_ERR");
        }
        ReleaseParams memory params = ReleaseParams({
            poolId: _position.poolId,
            marginForOne: _position.marginForOne,
            payer: address(this),
            releaseAmount: releaseAmount,
            repayAmount: 1,
            borrowAmount: 1,
            deadline: block.timestamp + 1000
        });
        hook.release{value: liquidateValue}(params);
        profit = _position.marginAmount + _position.marginTotal - releaseAmount;
        if (profit > 0) {
            marginToken.transfer(address(this), msg.sender, profit);
        }
        _burnPosition(positionId);
    }

    function liquidate(uint256 positionId) external returns (uint256 profit) {
        (bool liquidated,) = checkLiquidate(positionId);
        if (!liquidated) {
            return profit;
        }
        MarginPosition memory _position = _positions[positionId];
        HookStatus memory _status = hook.getStatus(_position.poolId);
        (Currency borrowToken, Currency marginToken) = _position.marginForOne
            ? (_status.key.currency0, _status.key.currency1)
            : (_status.key.currency1, _status.key.currency0);
        uint256 rateLast = hook.getBorrowRateCumulativeLast(_position.poolId, _position.marginForOne);
        uint256 borrowAmount = _position.borrowAmount * rateLast / _position.rateCumulativeLast;
        require(checkAmount(borrowToken, msg.sender, address(hook), borrowAmount), "INSUFFICIENT_AMOUNT");
        uint256 liquidateValue = 0;
        if (borrowToken == CurrencyLibrary.ADDRESS_ZERO) {
            liquidateValue = borrowAmount;
        }
        ReleaseParams memory params = ReleaseParams({
            poolId: _position.poolId,
            marginForOne: _position.marginForOne,
            payer: msg.sender,
            repayAmount: borrowAmount,
            borrowAmount: borrowAmount,
            releaseAmount: 0,
            deadline: block.timestamp + 1000
        });
        hook.release{value: liquidateValue}(params);
        profit = _position.marginAmount + _position.marginTotal;
        marginToken.transfer(address(this), msg.sender, profit);
        _burnPosition(positionId);
    }

    function withdrawFee(address token, address to, uint256 amount) external onlyOwner returns (bool success) {
        success = Currency.wrap(token).transfer(to, address(this), amount);
    }

    receive() external payable {}
}
