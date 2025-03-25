// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import { Currency } from "lib/v4-periphery/lib/v4-core/src/types/Currency.sol";
import { BalanceDeltaLibrary, BalanceDelta } from "lib/v4-periphery/lib/v4-core/src/types/BalanceDelta.sol";
import { PoolIdLibrary, PoolId} from "lib/v4-periphery/lib/v4-core/src/types/PoolId.sol";
import {PoolKey} from "lib/v4-periphery/lib/v4-core/src/types/PoolKey.sol";
import {CurrencyPoolLibrary} from "src/libraries/CurrencyPoolLibrary.sol";

contract Helper {
    function callFallback(address to, uint256 amount) external payable {
        require(msg.value == amount, "must transfer native amount");
        (bool success, ) = to.call{value: amount}("");
        require(success, "Native Transfer Failed");
    }
    
    function fromCurrency(Currency currency) public pure returns (address) {
        return Currency.unwrap(currency);
    }

    function toCurrency(address token) public pure returns (Currency) {
        return Currency.wrap(token);
    }

    function amount0(BalanceDelta balanceDelta) external pure returns (int128) {
        return BalanceDeltaLibrary.amount0(balanceDelta);
    }

    function amount1(BalanceDelta balanceDelta) external pure returns (int128) {
        return BalanceDeltaLibrary.amount1(balanceDelta);
    }

    function PoolKeyToId(PoolKey memory poolKey) external pure returns (PoolId) {
        return PoolIdLibrary.toId(poolKey);
    }

    function toTokenId(Currency currency, PoolKey memory key) external pure returns (uint256) {
        return CurrencyPoolLibrary.toTokenId(currency, key);
    }
}