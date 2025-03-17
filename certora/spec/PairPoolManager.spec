import "./CVLERC20.spec";
import "./MathSummary.spec";
import "./PoolManager.spec";

using PairPoolManager as PairPoolManager;
use rule removeLiquidityEndsWithZeroVirtualAccounting;
use rule addLiquidityEndsWithZeroVirtualAccounting;
use rule releaseEndsWithZeroVirtualAccounting;
use invariant ValidStatusInitializedPools;

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
        PairPoolManager.handleMargin(address,address,PairPoolManager.MarginParamsVo),
        PairPoolManager.handleSwapMirror(address,PoolManager.Currency,uint256),
        PairPoolManager.handleCollectFees(address,PoolManager.Currency ,uint256)
    ] default HAVOC_ECF;
}

// excluding methods whose body is just `revert <msg>';
use builtin rule sanity filtered{f -> !alwaysReverting(f) && f.contract != PM}
/*
rule alwaysRevert(method f) filtered{f -> alwaysReverting(f)}
{
    env e;
    calldataarg args;
    f@withrevert(e,args);

    assert lastReverted;
}*/
