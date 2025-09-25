import "./CVLERC20.spec";
import "./MathSummary.spec";
import "./PoolManager.spec";
import "./PoolStatusManager.spec";
import "./getAmountsSummary.spec";

/*
 * @title No Non-Zero Currency Deltas after Locking of PoolManager for methods: addLiquidity, removeLiquidity, release, collect, swapMirror and margin
 * @status Verified after fix
 * @notice 
 * @report https://prover.certora.com/output/497546/76bfd46d069d41fc83e5b23d0dde2df4?anonymousKey=462ac02b627c982377a9f27f587e80ca2307b584
 */


using PairPoolManager as PairPoolManager;
using LendingPoolManager as LendingPoolManager;
using MirrorTokenManager as MirrorTokenManager;
using MarginLiquidity as MarginLiquidity;
using Fallback as Fallback;
using PoolManager as PoolManager;
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
        PairPoolManager.handleRelease(PoolStatusManager.PoolStatus,PairPoolManager.ReleaseParams),
        PairPoolManager.handleAddLiquidity(address,PoolManager.PoolKey,uint256,uint256),
        PairPoolManager.handleRemoveLiquidity(address,PoolManager.PoolKey,uint256,uint256),
        PairPoolManager.handleMargin(address,address,PoolStatusManager.PoolStatus,PairPoolManager.MarginParamsVo),
        PairPoolManager.handleSwapMirror(address,PoolManager.Currency,uint256),
        PairPoolManager.handleCollectFees(address,PoolManager.Currency ,uint256)
    ] default HAVOC_ECF;
    /// Unresolved unlock callbacks (LendingPoolManager):
    unresolved external in LendingPoolManager.unlockCallback(bytes) => DISPATCH [
        LendingPoolManager.handleWithdraw(address,address,PoolManager.PoolId,PoolManager.Currency,uint256),
        LendingPoolManager.handleDeposit(address,address,PoolManager.PoolId,PoolManager.Currency,uint256)
    ] default HAVOC_ECF;


    //  we don't have an implementation around for `IMarginOracleReader`, it seems
    function _.observeNow(address /*IPairPoolManager*/, PoolStatusManager.PoolStatus /*status*/) external 
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

    function _.marginLiquidity() external => DISPATCHER(true) UNRESOLVED;
    function _.statusManager() external => DISPATCHER(true) UNRESOLVED;
    function _.getMarginReserves(address, PoolManager.PoolId, PoolStatusManager.PoolStatus) external => NONDET UNRESOLVED;
    function _.getInterestReserves(address, PoolManager.PoolId, PoolStatusManager.PoolStatus) external => NONDET UNRESOLVED;
}

methods {
    function PoolStatusManager.getAmountOut(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountIn) external returns (uint256,uint24,uint256) with (env e)
        => getAmountOutCVL(e.block.timestamp, status, zeroForOne, amountIn) DELETE;

    function PoolStatusManager.getAmountIn(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountOut) external returns (uint256,uint24,uint256) with (env e)
        => getAmountInCVL(e.block.timestamp, status, zeroForOne, amountOut) DELETE;

    function _.getAmountOut(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountIn) external with (env e)
        => getAmountOutCVL(e.block.timestamp, status, zeroForOne, amountIn) expect (uint256,uint24,uint256);

    function _.getAmountIn(PoolStatusManager.PoolStatus status, bool zeroForOne, uint256 amountOut) external with (env e)
        => getAmountInCVL(e.block.timestamp, status, zeroForOne, amountOut) expect (uint256,uint24,uint256);

    function MarginFees.getBorrowRateCumulativeLast(PoolStatusManager.PoolStatus) external returns (uint256,uint256)
       => NONDET;

    function MarginLiquidity.getInterestReserves(address, PairPoolManager.PoolId, PairPoolManager.PoolStatus) external returns (uint256, uint256)
        => NONDET;

    function PoolStatusManager._updateInterest0(PairPoolManager.PoolStatus memory, uint256, uint256) internal returns (PairPoolManager.InterestBalance memory) 
        => interestBalanceCVL();

    function PoolStatusManager._updateInterest1(PairPoolManager.PoolStatus memory, uint256, uint256) internal returns (PairPoolManager.InterestBalance memory) 
        => interestBalanceCVL();

    function PoolStatusManager._updateInterests(PairPoolManager.PoolStatus storage) internal 
        => noOp();
}
    
function noOp() {}

function interestBalanceCVL() returns PairPoolManager.InterestBalance {

    PairPoolManager.InterestBalance res;

    require res.allInterest == 0;
    require res.pairInterest == 0;
    require res.lendingInterest == 0;
    require res.protocolInterest == 0;

    return res;
}

function observeNowCVL() returns (uint224, uint256) {
    uint224 nondet1;
    uint256 nondet2;
    return (nondet1, nondet2);
}

function pairPoolManagerCVL(address callee) returns address {
    if (callee == PoolStatusManager) {
        return PoolStatusManager.pairPoolManager; 
    } else if(callee == LendingPoolManager) {
        return LendingPoolManager.pairPoolManager;
    } else {
        assert false;
        return 0;
    }
}