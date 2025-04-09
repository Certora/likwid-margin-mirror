import "./CVLERC20.spec";
import "./MathSummary.spec";
import "./PoolManager.spec";
import "./PoolStatusManager.spec";
import "./getAmountsSummary.spec";

using PairPoolManager as PairPoolManager;
using LendingPoolManager as LendingPoolManager;
using MirrorTokenManager as MirrorTokenManager;
using MarginLiquidity as MarginLiquidity; 
using Fallback as Fallback;
using PoolManager as PoolManager;

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
        LendingPoolManager.handleDeposit(address,address,PoolManager.PoolId,PoolManager.Currency,uint256),
        LendingPoolManager.handleBalanceMirror(address,PoolManager.PoolId,PoolManager.Currency,uint256)
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

// excluding methods whose body is just `revert <msg>';
use builtin rule sanity filtered{ f -> 
    !alwaysReverting(f) 
        && f.contract != PM 
        && f.contract == currentContract
        }

rule depositEndsWithZeroVirtualAccounting() {
    env e;
    address sender; require sender != PM;
    address recipient;
    PoolManager.PoolId poolId;
    PoolManager.Currency currency; 
    uint256 amount;
    requireInvariant ValidStatusInitializedPools(poolId);
    require ValidTimestamp(e);
    
    require zeroCurrencyDeltaForAll();
        env eSync;
        PM.sync(eSync, Helper.toCurrency(PM._synchedCurrency));
        LendingPoolManager.deposit(e, sender, recipient, poolId, currency, amount);
    assert zeroCurrencyDeltaForAll();
}

rule withdrawEndsWithZeroVirtualAccounting() {
    env e;
    address recipient;
    PoolManager.PoolId poolId;
    PoolManager.Currency currency; 
    uint256 amount;
    requireInvariant ValidStatusInitializedPools(poolId);
    require ValidTimestamp(e);
    
    require zeroCurrencyDeltaForAll();
        env eSync;
        PM.sync(eSync, Helper.toCurrency(PM._synchedCurrency));
        LendingPoolManager.withdraw(e, recipient, poolId, currency, amount);
    assert zeroCurrencyDeltaForAll();
}

rule balanceMirrorEndsWithZeroVirtualAccounting() {
    env e;
    require e.msg.sender != PM;
    PoolManager.PoolId poolId;
    PoolManager.Currency currency; 
    uint256 amount;
    requireInvariant ValidStatusInitializedPools(poolId);
    require ValidTimestamp(e);
    
    require zeroCurrencyDeltaForAll();
        env eSync;
        PM.sync(eSync, Helper.toCurrency(PM._synchedCurrency));
        LendingPoolManager.balanceMirror(e, poolId, currency, amount);
    assert zeroCurrencyDeltaForAll();
}

rule depositWithdrawsOthersBalance(PoolManager.PoolId poolId, bool zeroForOne)
{
    env e;
    address sender; require sender != PM;
    address recipient;
    address otherUser;

    uint256 amount; 

    PairPoolManager.PoolKey key = PoolStatusManager.getKey(poolId);
    uint256 currency0ID = Helper.toId(key.currency0);

    uint256 preBalance = PoolManager.balanceOf(otherUser, currency0ID);

    LendingPoolManager.deposit(e, sender, recipient, poolId, key.currency0, amount);

    uint256 postBalance = PoolManager.balanceOf(otherUser, currency0ID);

    assert otherUser != sender && otherUser != recipient => preBalance == postBalance; 
}