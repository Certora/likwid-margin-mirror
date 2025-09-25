using PoolStatusManager as PoolStatusManager;

methods {
    function PoolStatusManager.getKey(PoolManager.PoolId) external returns (PoolManager.PoolKey memory) envfree;
}

/// This setup assumes that at most two distinct poolIDs are accessed in the PoolStatusManager.statusStore storage.
ghost PoolManager.PoolId PoolID1;
ghost PoolManager.PoolId PoolID2;

definition isCustomID(PoolManager.PoolId poolId) returns bool = poolId == PoolID1 || poolId ==  PoolID2;

hook Sload PoolManager.Currency currency1 PoolStatusManager.statusStore[KEY PoolManager.PoolId poolId].key.currency1 {
    require isCustomID(poolId);
}

hook Sstore PoolStatusManager.statusStore[KEY PoolManager.PoolId poolId].key.currency1 PoolManager.Currency currency1 {
    require isCustomID(poolId);
}

hook Sload PoolManager.Currency currency0 PoolStatusManager.statusStore[KEY PoolManager.PoolId poolId].key.currency0 {
    require isCustomID(poolId);
}

hook Sstore PoolStatusManager.statusStore[KEY PoolManager.PoolId poolId].key.currency0 PoolManager.Currency currency0 {
    require isCustomID(poolId);
}