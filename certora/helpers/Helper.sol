// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import { Currency } from "lib/v4-periphery/lib/v4-core/src/types/Currency.sol";
import { BalanceDeltaLibrary, BalanceDelta } from "lib/v4-periphery/lib/v4-core/src/types/BalanceDelta.sol";
import { PoolIdLibrary, PoolId} from "lib/v4-periphery/lib/v4-core/src/types/PoolId.sol";
import {PoolKey} from "lib/v4-periphery/lib/v4-core/src/types/PoolKey.sol";
import {CurrencyPoolLibrary} from "src/libraries/CurrencyPoolLibrary.sol";
import {UQ112x112} from "src/libraries/UQ112x112.sol";
import {SafeCast} from "lib/v4-periphery/lib/v4-core/src/libraries/SafeCast.sol";

contract Helper {
    using SafeCast for uint256;
    using UQ112x112 for *;

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

    function getPriceX112FromReserves(uint256 _reserve0, uint256 _reserve1) external pure returns (uint224 price0X112, uint224 price1X112)
    {
        price0X112 = UQ112x112.encode(_reserve1.toUint112()).div(_reserve0.toUint112());
        price1X112 = UQ112x112.encode(_reserve0.toUint112()).div(_reserve1.toUint112());
    }
}