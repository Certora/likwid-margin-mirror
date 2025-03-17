import "./CVLERC20.spec";
import "./MathSummary.spec";
import "./PoolManager.spec"; 

methods {
    function PoolStatusManager.getStatus(PoolManager.PoolId poolId) external returns (PoolStatusManager.PoolStatus memory) envfree;
    
    /// Unresolved unlock callback:
    function _.unlockCallback(bytes) external => DISPATCHER(true);

    /// Unresolved unlock callback in PM:
    unresolved external in PoolManager.unlock(bytes) => DISPATCH [
        PairPoolManager.unlockCallback(bytes),
        MarginRouter.unlockCallback(bytes)
    ] default HAVOC_ECF;
    /// Unresolved unlock callbacks:
    unresolved external in PairPoolManager.unlockCallback(bytes) => DISPATCH [
        PairPoolManager.handleRelease(PairPoolManager.ReleaseParams),
        PairPoolManager.handleAddLiquidity(address,PoolManager.PoolKey,uint256,uint256),
        PairPoolManager.handleRemoveLiquidity(address,PoolManager.PoolKey,uint256,uint256),
        PairPoolManager.handleMargin(address,address,PairPoolManager.MarginParamsVo)
    ] default HAVOC_ECF;
    
    unresolved external in MarginRouter.unlockCallback(bytes) => DISPATCH [
        MarginRouter.handelSwap(address,MarginRouter.SwapParams)
    ] default HAVOC_ECF;

    /// This one is intended to solve the unresolution of the hook call to `beforeSwap` from within PoolManager.swap()
    unresolved external in PoolManager.swap(PoolManager.PoolKey,IPoolManager.SwapParams,bytes) => DISPATCH [
        Hook.beforeSwap(address,PoolManager.PoolKey,IPoolManager.SwapParams,bytes)
    ] default HAVOC_ECF;
}

use builtin rule sanity filtered{f -> f.contract == currentContract}

invariant ValidStatusKeysHooks(PoolManager.PoolId poolId)
    PoolStatusManager.statusStore[poolId].key.hooks == 0 || PoolStatusManager.statusStore[poolId].key.hooks == Hook
    filtered{f -> f.contract == Hook}

/// For a non-zero amountIn, the amount out should also be non-zero.
/// Inner-assert: the call to swap() should not involve any non-zero amount to be swapped within PoolManager. 
rule swapCorrectness() {
    env e;
    MarginRouter.SwapParams params;
    PoolStatusManager.PoolStatus status = PoolStatusManager.getStatus(params.poolId);
    /// Prove this is correct.
    require status.key.hooks == Hook;
    uint256 amountOut = exactInput(e, params);

    satisfy amountOut > 0;
}