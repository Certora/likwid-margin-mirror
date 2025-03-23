import "./CVLERC20.spec";
import "./MathSummary.spec";
import "./PoolManager.spec";
import "./PoolStatusManager.spec";

using PairPoolManager as PairPoolManager;
using LendingPoolManager as LendingPoolManager;
using MirrorTokenManager as MirrorTokenManager;
use rule removeLiquidityEndsWithZeroVirtualAccounting;
use rule addLiquidityEndsWithZeroVirtualAccounting;
use rule releaseEndsWithZeroVirtualAccounting;
use rule collectProtocolFeesEndsWithZeroVirtualAccounting;
use rule swapMirrorEndsWithZeroVirtualAccounting;
use rule marginEndsWithZeroVirtualAccounting;
use invariant ValidStatusInitializedPools filtered{f -> !calledByHook(f) && f.selector != sig:PairPoolManager.unlockCallback(bytes).selector}

methods {
    /// Unresolved unlock callback:
    function _.unlockCallback(bytes) external => DISPATCHER(true);

    /// Unresolved unlock callback in PM:
    unresolved external in PoolManager.unlock(bytes) => DISPATCH [
        PairPoolManager.unlockCallback(bytes),
        LendingPoolManager.unlockCallback(bytes)
    ] default HAVOC_ECF;
    /// Unresolved unlock callbacks (PairPoolManager):
    unresolved external in PairPoolManager.unlockCallback(bytes) => DISPATCH [
        PairPoolManager.handleRelease(PairPoolManager.ReleaseParams),
        PairPoolManager.handleAddLiquidity(address,PoolManager.PoolKey,uint256,uint256),
        PairPoolManager.handleRemoveLiquidity(address,PoolManager.PoolKey,uint256,uint256),
        PairPoolManager.handleMargin(address,address,PairPoolManager.MarginParamsVo),
        PairPoolManager.handleSwapMirror(address,PoolManager.Currency,uint256),
        PairPoolManager.handleCollectFees(address,PoolManager.Currency ,uint256)
    ] default HAVOC_ECF;
    /// Unresolved unlock callbacks (LendingPoolManager):
    unresolved external in LendingPoolManager.unlockCallback(bytes) => DISPATCH [
        LendingPoolManager.handleWithdraw(address,address,PoolManager.PoolId,PoolManager.Currency,uint256),
        LendingPoolManager.handleDeposit(address,address,PoolManager.PoolId,PoolManager.Currency,uint256)
    ] default HAVOC_ECF;


    //  we don't have an implementation around for `IMarginOracleReader`, it seems
    function _.observeNow(address /*IPairPoolManager*/ poolManager, PoolManager.PoolId id) external 
        => observeNowCVL() expect (uint224, uint256);


    //  we don't have an implementation around for `IMarginOracleWriter`, it seems
    function _.write(PoolManager.PoolKey /*calldata*/ key, uint112 reserve0, uint112 reserve1) external 
        => NONDET; // TODO model side effects


    // declared in `IStatusBase`, we have the implementation in `PoolStatusManager <: IPoolStatusManager <: IStatusBase`
    // this is called on `e.msg.sender` in places, not sure how to link, so doing a manual dispatcher
    function _.pairPoolManager() external /* view returns (address) */ 
        => pairPoolManagerCVL(calledContract) expect address;

    /// Has only internal effects in MirrorTokenManager.
    function _.setOperator(address,bool) external => NONDET UNRESOLVED;

}

function observeNowCVL() returns (uint224, uint256) {
    uint224 nondet1;
    uint256 nondet2;
    return (nondet1, nondet2);
}

function pairPoolManagerCVL(address callee) returns address {
    if (callee == PoolStatusManager) {
        return PoolStatusManager.pairPoolManager; 
    } else {
        assert false;
        return 0;
    }
}

// excluding methods whose body is just `revert <msg>';
use builtin rule sanity filtered{ f -> 
    !alwaysReverting(f) 
        && f.contract != PM 
        && f.contract == currentContract
        }
/*
rule alwaysRevert(method f) filtered{f -> alwaysReverting(f)}
{
    env e;
    calldataarg args;
    f@withrevert(e,args);

    assert lastReverted;
}*/
