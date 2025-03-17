using PoolManager as PM;
using PoolStatusManager as PoolStatusManager;
using MarginHook as Hook;

methods {
    function PM._swap(int256 amountToSwap) internal returns (int256) => assertZeroDelta(amountToSwap);
    /// Pure function is summarized by a generic arbitrary mapping - this is logically sound.
    function Hooks.hasPermission(address self, uint160 flag) internal returns (bool) => CVLHasPermission(self, flag);
}

definition BEFORE_SWAP_FLAG() returns uint160 = 1 << 7;
definition AFTER_SWAP_FLAG() returns uint160 = 1 << 6;
definition BEFORE_SWAP_RETURNS_DELTA_FLAG() returns uint160 = 1 << 3;
definition AFTER_SWAP_RETURNS_DELTA_FLAG() returns uint160 = 1 << 2;
definition BEFORE_ADD_LIQUIDITY_FLAG() returns uint160 = 1 << 11;

persistent ghost CVLHasPermission(address,uint160) returns bool {
    /// Fix the permissions based on the MarginHook.
    axiom CVLHasPermission(Hook, BEFORE_SWAP_FLAG()) == true;
    axiom CVLHasPermission(Hook, BEFORE_SWAP_RETURNS_DELTA_FLAG()) == true;
    axiom CVLHasPermission(Hook, AFTER_SWAP_FLAG()) == false;
    axiom CVLHasPermission(Hook, AFTER_SWAP_RETURNS_DELTA_FLAG()) == false;
    axiom CVLHasPermission(Hook, BEFORE_ADD_LIQUIDITY_FLAG()) == true;
}

definition alwaysReverting(method f) returns bool = false
    || f.selector == sig:Hook.beforeRemoveLiquidity(address,PoolManager.PoolKey,IPoolManager.ModifyLiquidityParams,bytes).selector
    || f.selector == sig:Hook.beforeAddLiquidity(address,PoolManager.PoolKey,IPoolManager.ModifyLiquidityParams,bytes).selector
    || f.selector == sig:Hook.afterSwap(address,PoolManager.PoolKey,IPoolManager.SwapParams,PoolManager.BalanceDelta,bytes).selector
    || f.selector == sig:Hook.afterRemoveLiquidity(address,PoolManager.PoolKey,IPoolManager.ModifyLiquidityParams,PoolManager.BalanceDelta,PoolManager.BalanceDelta,bytes).selector
    || f.selector == sig:Hook.afterAddLiquidity(address,PoolManager.PoolKey,IPoolManager.ModifyLiquidityParams,PoolManager.BalanceDelta,PoolManager.BalanceDelta,bytes).selector
    || f.selector == sig:Hook.afterInitialize(address,PoolManager.PoolKey,uint160,int24).selector
    || f.selector == sig:Hook.beforeDonate(address,PoolManager.PoolKey,uint256,uint256,bytes).selector
    || f.selector == sig:Hook.afterDonate(address,PoolManager.PoolKey,uint256,uint256,bytes).selector;

function zeroCurrencyDeltaForAll() returns bool {
    /// Overall require on storage by direct access.
    return forall address token. forall address account. PM._currencyDelta[token][account] == 0;
}

/// Since there is no liquidity in pools in the PoolManager, the hook should never pass a non-zero amount to be swapped.
function assertZeroDelta(int256 amountToSwap) returns int256 {
    assert amountToSwap == 0, "The hook must not pass any amount to the pool swap function";
    return 0;
}

/// @title Unlocking the PoolManager in removeLiquidity() should always result in zeroed-out virtual accounting.
rule removeLiquidityEndsWithZeroVirtualAccounting()
{
    env e;
    PairPoolManager.RemoveLiquidityParams params;
    require PoolStatusManager.statusStore[params.poolId].key.hooks == PairPoolManager;
    
    require zeroCurrencyDeltaForAll();
        PairPoolManager.removeLiquidity(e, params);
    assert zeroCurrencyDeltaForAll();
}

/// @title Unlocking the PoolManager in addLiquidity() should always result in zeroed-out virtual accounting.
rule addLiquidityEndsWithZeroVirtualAccounting()
{
    env e;
    require e.msg.sender != PM;
    PairPoolManager.AddLiquidityParams params;
    require PoolStatusManager.statusStore[params.poolId].key.hooks == PairPoolManager;
    
    require zeroCurrencyDeltaForAll();
        PairPoolManager.addLiquidity(e, params);
    assert zeroCurrencyDeltaForAll();
}

/// @title Unlocking the PoolManager in release() should always result in zeroed-out virtual accounting.
rule releaseEndsWithZeroVirtualAccounting()
{
    env e;
    require e.msg.sender != PM;
    PairPoolManager.ReleaseParams params;
    require PoolStatusManager.statusStore[params.poolId].key.hooks == PairPoolManager;
    
    require zeroCurrencyDeltaForAll();
        PairPoolManager.release(e, params);
    assert zeroCurrencyDeltaForAll();
}