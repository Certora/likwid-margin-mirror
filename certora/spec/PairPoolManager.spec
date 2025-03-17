import "./CVLERC20.spec";
import "./MathSummary.spec";
import "./PoolManager.spec";

using PairPoolManager as PairPoolManager;
use rule removeLiquidityEndsWithZeroVirtualAccounting;
use rule addLiquidityEndsWithZeroVirtualAccounting;
use rule releaseEndsWithZeroVirtualAccounting;

methods {
    /// Unresolved unlock callback:
    function _.unlockCallback(bytes) external => DISPATCHER(true);

    /// Unresolved unlock callback in PM:
    unresolved external in PoolManager.unlock(bytes) => DISPATCH [
        PairPoolManager.unlockCallback(bytes)
    ] default HAVOC_ECF;
    /// Unresolved unlock callbacks:
    unresolved external in PairPoolManager.unlockCallback(bytes) => DISPATCH [
        PairPoolManager.handleRelease(PairPoolManager.ReleaseParams),
        PairPoolManager.handleAddLiquidity(address,PoolManager.PoolKey,uint256,uint256),
        PairPoolManager.handleRemoveLiquidity(address,PoolManager.PoolKey,uint256,uint256),
        PairPoolManager.handleMargin(address,address,PairPoolManager.MarginParamsVo)
    ] default HAVOC_ECF;
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

// excluding methods whose body is just `revert <msg>';
use builtin rule sanity filtered{f -> !alwaysReverting(f) && f.contract != PM}

rule alwaysRevert(method f) filtered{f -> alwaysReverting(f)}
{
    env e;
    calldataarg args;
    f@withrevert(e,args);

    assert lastReverted;
}
