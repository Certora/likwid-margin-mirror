// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../../src/PairPoolManager.sol";
import {BaseHook} from "v4-periphery/src/base/hooks/BaseHook.sol";
import {Owned} from "solmate/src/auth/Owned.sol";

contract PairPoolManagerHarness is PairPoolManager {

    constructor(
        address initialOwner,
        IPoolManager _manager,
        IMirrorTokenManager _mirrorTokenManager,
        ILendingPoolManager _lendingPoolManager,
        IMarginLiquidity _marginLiquidity,
        IMarginFees _marginFees
    ) PairPoolManager(initialOwner, _manager, _mirrorTokenManager, _lendingPoolManager, _marginLiquidity, _marginFees) 
    {}

    // function getBalances(PoolKey memory key) external view returns (BalanceStatus memory balanceStatus) {
    //     return _getBalances(key);
    // }

    function getSupplies(uint256 uPoolId) external
        view
        returns (uint256 totalSupply, uint256 retainSupply0, uint256 retainSupply1)
    {
        return marginLiquidity.getSupplies(uPoolId);
    }

    function getPoolId(PoolId poolId) external view returns (uint256 uPoolId) {
        return marginLiquidity.getPoolId(poolId);
    }
}