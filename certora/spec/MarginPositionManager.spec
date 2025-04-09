import "./CVLERC20.spec";
import "./MathSummary.spec";
import "./PoolStatusManager.spec";

using MarginPositionManager as Position;

methods {
    function PairPoolManager.margin(address sender, PoolStatusManager.PoolStatus status, MarginPositionManager.MarginParamsVo paramsVo) external
        returns (MarginPositionManager.MarginParamsVo) with (env e) => verifyMarginCall(e.msg.sender, sender, status, paramsVo);

    function PairPoolManager.setBalances(PoolManager.PoolId poolId) external
        returns (PoolStatusManager.PoolStatus) with (env e) => setBalancesSummary(e.msg.sender, poolId);

    function Helper.PoolKeyToId(PoolManager.PoolKey) external returns (PoolManager.PoolId) envfree;
}

function equalKeys(PoolStatusManager.PoolKey keyA, PoolStatusManager.PoolKey keyB) returns bool {
    return keyA.currency0 == keyB.currency0 &&
        keyA.currency1 == keyB.currency1 &&
        keyA.hooks == keyB.hooks &&
        keyA.fee == keyB.fee;
        /// We don't care about key.tickSpacing.
}

function setBalancesSummary(address caller, PoolManager.PoolId poolId) returns PoolStatusManager.PoolStatus {
    PoolStatusManager.PoolStatus status;
    assert caller == Position;
    /// Is proven in setBalancesCorrectStatusKey
    require Helper.PoolKeyToId(status.key) == poolId;
    return status;
}

function verifyMarginCall(address caller, address sender, PoolStatusManager.PoolStatus status, MarginPositionManager.MarginParamsVo paramsVo) 
returns MarginPositionManager.MarginParamsVo {
    assert caller == Position;
    assert Helper.PoolKeyToId(status.key) == paramsVo.params.poolId;

    return paramsVo;
}

rule setBalancesCorrectStatusKey(PoolManager.PoolId poolId) 
{
    env e;
    requireInvariant StatusStorePoolKeyMatch(poolId);
    PoolStatusManager.PoolStatus status = PoolStatusManager.setBalances(e, poolId);
    assert Helper.PoolKeyToId(status.key) == poolId;
}

/*
 * @title for every initialized pool stored in PoolStatusManager.statusStore, its poolId and poolKey are consistent with each other
 * @status Verified
 * @notice 
 * @report https://prover.certora.com/output/497546/6412b5d009f0497aae1af547ab22f080?anonymousKey=a6aff146a944c9780ad412a8dc1405ebe21e15f5
 */
invariant StatusStorePoolKeyMatch(PoolManager.PoolId poolId)
    (PoolStatusManager.statusStore[poolId].key.currency1 != 0 => Helper.PoolKeyToId(PoolStatusManager.getKey(poolId)) == poolId)
    &&
    (PoolStatusManager.statusStore[poolId].key.currency1 == 0 => 
        PoolStatusManager.statusStore[poolId].key.currency0 == 0 &&
        PoolStatusManager.statusStore[poolId].key.fee == 0 &&
        PoolStatusManager.statusStore[poolId].key.hooks == 0)
    filtered{f -> f.contract == PoolStatusManager}
    {
        preserved PoolStatusManager.initialize(PoolManager.PoolKey key) with (env e) {
            /// Is forced by PoolManager.initialize()
            require key.currency1 > 0;
        }
    }

/// Will call verifyMarginCall()
rule margin_inputCheck(MarginPositionManager.MarginParams params)
{
    env e;
    Position.margin(e, params);

    satisfy true;
}