import "./CVLERC20.spec";
import "./MathSummary.spec";
import "./PoolManager.spec";
import "./PoolStatusManager.spec";
import "./getAmountsSummary.spec";

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
}

definition isUnlockCallback(method f) returns bool = 
    f.selector == sig:LendingPoolManager.unlockCallback(bytes).selector ||
    f.selector == sig:PairPoolManager.unlockCallback(bytes).selector;

definition hardMethods(method f) returns bool = 
    f.selector == sig:PairPoolManager.addLiquidity(PairPoolManager.AddLiquidityParams).selector ||
    f.selector == sig:PairPoolManager.removeLiquidity(PairPoolManager.RemoveLiquidityParams).selector ||
    f.selector == sig:PairPoolManager.swapMirror(address,address,PoolManager.PoolId,bool,uint256).selector ||
    f.selector == sig:PairPoolManager.mirrorInRealOut(PoolManager.PoolId,PoolManager.Currency,uint256).selector;

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

/// @title The rate cumulative last value can never decrease, for any pool.
/// Timeouts may be resolved by summarizing mulDiv with MathSummary.spec/mulDivLIA.
rule rateCumulativeCannotDecrease(PoolManager.PoolId poolId, method f) 
filtered{f -> !f.isView && f.contract == PairPoolManager && !isUnlockCallback(f)} {
    requireInvariant ValidStatusInitializedPools(poolId);
    mathint rateCumulative0_pre = PoolStatusManager.statusStore[poolId].rate0CumulativeLast;
    mathint rateCumulative1_pre = PoolStatusManager.statusStore[poolId].rate1CumulativeLast;
        env e;
        calldataarg args;
        f(e, args);
    mathint rateCumulative0_post = PoolStatusManager.statusStore[poolId].rate0CumulativeLast;
    mathint rateCumulative1_post = PoolStatusManager.statusStore[poolId].rate1CumulativeLast;

    assert rateCumulative1_post >= rateCumulative1_pre && rateCumulative0_post >= rateCumulative0_pre;
}

rule addingLiquidityHasZeroEffectOnOtherPools(PoolManager.PoolId poolId, bool zeroForOne)
{
    env e;
    uint256 reserve0;
    uint256 reserve1;
    reserve0, reserve1 = getReserves(e, poolId);
    uint256 quote_amount = assert_uint256(min((zeroForOne ? reserve1 : reserve0)/2, 10^6));

    uint256 amountIn_pre = PairPoolManager.getAmountIn(e, poolId, zeroForOne, quote_amount);
        PairPoolManager.AddLiquidityParams params;
        requireInvariant ValidStatusInitializedPools(params.poolId);
        requireInvariant ValidStatusInitializedPools(poolId);
        PairPoolManager.addLiquidity(e, params);
    uint256 amountIn_post = PairPoolManager.getAmountIn(e, poolId, zeroForOne, quote_amount);

    assert params.poolId != poolId => amountIn_post == amountIn_pre;
}

rule removingLiquidityHasZeroEffectOnOtherPools(PoolManager.PoolId poolId, bool zeroForOne)
{
    env e;
    uint256 reserve0;
    uint256 reserve1;
    reserve0, reserve1 = getReserves(e, poolId);
    uint256 quote_amount = assert_uint256(min((zeroForOne ? reserve1 : reserve0)/2, 10^6));

    uint256 amountIn_pre = PairPoolManager.getAmountIn(e, poolId, zeroForOne, quote_amount);
        PairPoolManager.RemoveLiquidityParams params;
        requireInvariant ValidStatusInitializedPools(params.poolId);
        requireInvariant ValidStatusInitializedPools(poolId);
        PairPoolManager.removeLiquidity(e, params);
    uint256 amountIn_post = PairPoolManager.getAmountIn(e, poolId, zeroForOne, quote_amount);

    assert params.poolId != poolId => amountIn_post == amountIn_pre;
}

/// @title addLiquidity() shouldn't change the price by more than the allowed error.
rule addLiquidityPriceStability(PoolManager.PoolId poolId, bool zeroForOne) 
{
    env e;
    uint256 reserve0_pre;
    uint256 reserve1_pre;
    uint224 price0X112_pre;
    uint224 price1X112_pre;
    reserve0_pre, reserve1_pre = PairPoolManager.getReserves(e, poolId);
    price0X112_pre, price1X112_pre = Helper.getPriceX112FromReserves(reserve0_pre, reserve1_pre);

        PairPoolManager.AddLiquidityParams params;
        require params.poolId == poolId;
        requireInvariant ValidStatusInitializedPools(params.poolId);
        PairPoolManager.addLiquidity(e, params);

    uint256 reserve0_post;
    uint256 reserve1_post;
    uint224 price0X112_post;
    uint224 price1X112_post;
    reserve0_post, reserve1_post = PairPoolManager.getReserves(e, poolId);
    price0X112_post, price1X112_post = Helper.getPriceX112FromReserves(reserve0_post, reserve1_post);

    assert abs(price0X112_post - price0X112_pre) <= 2;
    assert abs(price1X112_post - price1X112_pre) <= 2;
}

/// @title removeLiquidity() shouldn't change the price by more than the allowed error.
rule removeLiquidityPriceStability(PoolManager.PoolId poolId, bool zeroForOne) 
{
    env e;
    uint256 reserve0_pre;
    uint256 reserve1_pre;
    uint224 price0X112_pre;
    uint224 price1X112_pre;
    reserve0_pre, reserve1_pre = PairPoolManager.getReserves(e, poolId);
    price0X112_pre, price1X112_pre = Helper.getPriceX112FromReserves(reserve0_pre, reserve1_pre);

        PairPoolManager.RemoveLiquidityParams params;
        require params.poolId == poolId;
        requireInvariant ValidStatusInitializedPools(params.poolId);
        PairPoolManager.removeLiquidity(e, params);
    
    uint256 reserve0_post;
    uint256 reserve1_post;
    uint224 price0X112_post;
    uint224 price1X112_post;
    reserve0_post, reserve1_post = PairPoolManager.getReserves(e, poolId);
    price0X112_post, price1X112_post = Helper.getPriceX112FromReserves(reserve0_post, reserve1_post);

    assert abs(price0X112_post - price0X112_pre) <= 2;
    assert abs(price1X112_post - price1X112_pre) <= 2;
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
