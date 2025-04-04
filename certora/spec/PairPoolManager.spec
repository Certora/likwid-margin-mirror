import "./CVLERC20.spec";
import "./MathSummary.spec";
import "./PoolManager.spec";
import "./PoolStatusManager.spec";
import "./getAmountsSummary.spec";

using PairPoolManager as PairPoolManager;
using LendingPoolManager as LendingPoolManager;
using MirrorTokenManager as MirrorTokenManager;
using MarginLiquidity as MarginLiquidity;
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

    function PoolStatusManager._updateInterest0(PairPoolManager.PoolStatus memory status, uint256, uint256) internal returns (PairPoolManager.InterestBalance memory) 
        => interestBalanceCVL();

    function PoolStatusManager._updateInterest1(PairPoolManager.PoolStatus memory status, uint256, uint256) internal returns (PairPoolManager.InterestBalance memory) 
        => interestBalanceCVL();

    function PoolStatusManager._updateInterests(PoolStatusManager.PoolStatus storage status) internal 
        => noOp();
}

definition isUnlockCallback(method f) returns bool = 
    f.selector == sig:LendingPoolManager.unlockCallback(bytes).selector ||
    f.selector == sig:PairPoolManager.unlockCallback(bytes).selector;

definition hardMethods(method f) returns bool = 
    f.selector == sig:PairPoolManager.addLiquidity(PairPoolManager.AddLiquidityParams).selector ||
    f.selector == sig:PairPoolManager.removeLiquidity(PairPoolManager.RemoveLiquidityParams).selector ||
    f.selector == sig:PairPoolManager.swapMirror(address,address,PoolManager.PoolId,bool,uint256).selector ||
    f.selector == sig:PairPoolManager.mirrorInRealOut(PoolManager.PoolId,PoolManager.Currency,uint256).selector;
    
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

rule marginDoesNotChangeBalances {
    env e;
    // calldataarg args;
    address sender;
    PairPoolManager.PoolStatus status;
    PairPoolManager.MarginParamsVo paramsVo;
    PairPoolManager.MarginParams params = paramsVo.params;

    uint256 preReserve0; 
    uint256 preReserve1; 
    (preReserve0, preReserve1) = getReserves(e, params.poolId);

    margin(e, sender, status, paramsVo);

    uint256 postReserve0; 
    uint256 postReserve1; 
    (postReserve0, postReserve1) = getReserves(e, params.poolId);

    assert preReserve0 == postReserve0;
    assert preReserve1 == postReserve1;
}

rule releaseDoesNotChangeBalances {
    env e;
    // calldataarg args;
    PairPoolManager.PoolStatus status;
    PairPoolManager.ReleaseParams params;

    uint256 preReserve0; 
    uint256 preReserve1; 
    (preReserve0, preReserve1) = getReserves(e, params.poolId);

    release(e, status, params);

    uint256 postReserve0; 
    uint256 postReserve1; 
    (postReserve0, postReserve1) = getReserves(e, params.poolId);

    assert preReserve0 == postReserve0;
    assert preReserve1 == postReserve1;
}


rule addLiquidityPreservesShares() {
    env e;
    PairPoolManager.AddLiquidityParams params;
    uint256 poolId = MarginLiquidity.getPoolId(e, params.poolId);

    uint256 preTotalSupply;
    // uint256 preTotalSupply_balanceOf;
    // uint256 preReserve0; 
    // uint256 preReserve1;
    // (preReserve0, preReserve1) = PairPoolManager.getReserves(e, params.poolId);
    // (preTotalSupply, _, _) = MarginLiquidity.getSupplies(e, poolId);
    preTotalSupply = MarginLiquidity.balanceOf(e, currentContract, poolId);
    
    // require preTotalSupply == preTotalSupply_balanceOf;

    addLiquidity(e, params);
    // uint256 id;
    // uint8 level;
    // uint256 amount;
    // MarginLiquidity.addLiquidity(e, currentContract, id, level, amount);

    uint256 postTotalSupply;
    // uint256 postReserve0; 
    // uint256 postReserve1;
    // (postReserve0, postReserve1) = PairPoolManager.getReserves(e, params.poolId);
    // (postTotalSupply, _, _) = MarginLiquidity.getSupplies(e, poolId);
    postTotalSupply = MarginLiquidity.balanceOf(e, currentContract, poolId);

    assert preTotalSupply <= postTotalSupply;
    // require preTotalSupply > 0;
    // require postReserve0 + postReserve1 > 0;
    // assert (preReserve0 + preReserve1) * postTotalSupply <= (postReserve0 + postReserve1) * preTotalSupply;
}

rule solvency(PairPoolManager.PoolId poolId, env e, method f) filtered{f -> !f.isView} {

    uint256 poolId_u256 = MarginLiquidity.getPoolId(e, poolId);
    uint256 preTotalSupply;
    uint256 preReserve0; 
    uint256 preReserve1;
    (preReserve0, preReserve1) = PairPoolManager.getReserves(e, poolId); 
    (preTotalSupply, _, _) = MarginLiquidity.getSupplies(e, poolId_u256); 

    require preReserve0 + preReserve1 >= preTotalSupply;

    calldataarg args; 
    f(e, args); 

    uint256 postTotalSupply;
    uint256 postReserve0; 
    uint256 postReserve1;
    (postReserve0, postReserve1) = PairPoolManager.getReserves(e, poolId); 
    (postTotalSupply, _, _) = MarginLiquidity.getSupplies(e, poolId_u256); 

    assert postReserve0 + postReserve1 >= postTotalSupply;
}

rule removeLiquidityPreservesShares() {
    env e;
    PairPoolManager.RemoveLiquidityParams params;

    uint256 poolId = MarginLiquidity.getPoolId(e, params.poolId);

    uint256 preTotalSupply;
    uint256 preReserve0; 
    uint256 preReserve1;
    (preReserve0, preReserve1) = PairPoolManager.getReserves(e, params.poolId);
    (preTotalSupply, _, _) = MarginLiquidity.getSupplies(e, poolId);

    removeLiquidity(e, params);

    uint256 postTotalSupply;
    uint256 postReserve0; 
    uint256 postReserve1;
    (postReserve0, postReserve1) = PairPoolManager.getReserves(e, params.poolId);
    (postTotalSupply, _, _) = MarginLiquidity.getSupplies(e, poolId);

    assert preTotalSupply >= postTotalSupply;
    assert (preReserve0 + preReserve1) * postTotalSupply == (postReserve0 + postReserve1) * preTotalSupply;
}

rule roundTripSwapResultsInLoss() {
    env e;
    
    address sender;
    PairPoolManager.PoolKey key;
    IPoolManager.SwapParams firstSwap;
    IPoolManager.SwapParams reverseSwap;
    
    // Store initial state
    mathint initialAmount = -(firstSwap.amountSpecified);
    
    // Rule setup requirements 
    require firstSwap.zeroForOne == true;
    require firstSwap.zeroForOne != reverseSwap.zeroForOne; // Swaps must be in opposite directions
    require firstSwap.amountSpecified < 0;

    // Execute first swap
    uint256 amountOut;
    (_, _, _, amountOut, _) = swap(e, sender, key, firstSwap);
    
    // Execute reverse swap using the output as input
    require reverseSwap.amountSpecified == -amountOut;
    uint256 finalAmount;
    (_, _, _, finalAmount, _) = swap(e, sender, key, reverseSwap);
    
    // Final amount should be less than initial due to fees
    assert finalAmount <= initialAmount;
}

rule roundTripSwapBasic() {
    env e;

    // initial reserves;
    uint256 reserveIn0;
    uint256 reserveOut0;
    require reserveIn0 > 0 && reserveOut0 > 0;
    
    // ------ forward swap -------

    // input amount for forward swap
    uint256 amountIn;

    // input amount after fees;
    uint256 amountInAfterFees;
    require amountInAfterFees <= amountIn;

    // output amount forward swap;
    uint256 amountOut = amountOutCVL(amountInAfterFees, reserveOut0, reserveIn0);

    // new reserves;
    uint256 reserveIn1;
    require reserveIn1 == reserveIn0 + amountInAfterFees;
    uint256 reserveOut1;
    require reserveOut1 == reserveOut0 - amountOut;

    // ------ reverse swap -------

    // input for reverse swap after fees
    uint256 amountOutAfterFees;
    require amountOutAfterFees <= amountOut;

    // output amount forward swap;
    uint256 finalAmount = amountOutCVL(amountOutAfterFees, reserveIn1, reserveOut1);

    assert finalAmount <= amountIn;
}

rule intergrityOfSetAndUpdateBalances() {
    env e;
    PairPoolManager.PoolKey key;
    PairPoolManager.PoolId poolId = Helper.PoolKeyToId(key);
    PairPoolManager.PoolStatus status = PoolStatusManager.getStatus(e, poolId);

    // require PoolStatusManager.blockTimestampLast != uint32(e.block.timestamp % (2 ** 32));
    // require status.blockTimestampLast == require_uint32(e.block.timestamp % (2 ^ 32));
    
    PoolStatusManager.updateBalances(e, key);

    uint256 preReserve0; 
    uint256 preReserve1; 
    (preReserve0, preReserve1) = getReserves(e, poolId);

    PoolStatusManager.setBalances(e, key);
    PoolStatusManager.updateBalances(e, key);

    uint256 postReserve0; 
    uint256 postReserve1; 
    (postReserve0, postReserve1) = getReserves(e, poolId);

    assert preReserve0 == postReserve0;
}