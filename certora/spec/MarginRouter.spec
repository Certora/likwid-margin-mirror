import "./CVLERC20.spec";
import "./MathSummary.spec";
import "./PoolManager.spec";

using MarginHookManager as Hook;

methods {
    function Hook.getStatus(PoolManager.PoolId poolId) external returns (MarginHookManager.HookStatus memory) envfree;
    
    /// Unresolved unlock callback:
    function _.unlockCallback(bytes) external => DISPATCHER(true);

    /// Unresolved unlock callback in PM:
    unresolved external in PoolManager.unlock(bytes) => DISPATCH [
        MarginHookManager.unlockCallback(bytes),
        MarginRouter.unlockCallback(bytes)
    ] default HAVOC_ECF;
    /// Unresolved unlock callbacks:
    unresolved external in MarginHookManager.unlockCallback(bytes) => DISPATCH [
        MarginHookManager.handleRelease(MarginHookManager.ReleaseParams),
        MarginHookManager.handleAddLiquidity(address,PoolManager.PoolKey,uint256,uint256),
        MarginHookManager.handleRemoveLiquidity(address,PoolManager.PoolKey,uint256,uint256),
        MarginHookManager.handleMargin(address,MarginHookManager.MarginParams)
    ] default HAVOC_ECF;
    
    unresolved external in MarginRouter.unlockCallback(bytes) => DISPATCH [
        MarginRouter.handelSwap(address,MarginRouter.SwapParams)
    ] default HAVOC_ECF;

    /// This one is intended to solve the unresolution of the hook call to `beforeSwap` from within PoolManager.swap()
    unresolved external in PoolManager.swap(PoolManager.PoolKey,IPoolManager.SwapParams,bytes) => DISPATCH [
        MarginHookManager.beforeSwap(address,PoolManager.PoolKey,IPoolManager.SwapParams,bytes)
    ] default HAVOC_ECF;
}

use builtin rule sanity filtered{f -> f.contract == currentContract}

invariant ValidStatusKeysHooks(PoolManager.PoolId poolId)
    Hook.hookStatusStore[poolId].key.hooks == 0 || Hook.hookStatusStore[poolId].key.hooks == Hook
    filtered{f -> f.contract == Hook}

/// For a non-zero amountIn, the amount out should also be non-zero.
/// Inner-assert: the call to swap() should not involve any non-zero amount to be swapped within PoolManager. 
rule swapCorrectness() {
    env e;
    MarginRouter.SwapParams params;
    MarginHookManager.HookStatus status = Hook.getStatus(params.poolId);
    /// Prove this is correct.
    require status.key.hooks == Hook;
    uint256 amountOut = exactInput(e, params);

    satisfy amountOut > 0;
}