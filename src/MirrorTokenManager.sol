// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.26;

import {ERC6909Claims} from "@uniswap/v4-core/src/ERC6909Claims.sol";
import {Owned} from "solmate/src/auth/Owned.sol";
import {PoolId} from "@uniswap/v4-core/src/types/PoolId.sol";
import {Currency, CurrencyLibrary} from "@uniswap/v4-core/src/types/Currency.sol";

import {IMarginPositionManager} from "./interfaces/IMarginPositionManager.sol";
import {IMirrorTokenManager} from "./interfaces/IMirrorTokenManager.sol";

contract MirrorTokenManager is IMirrorTokenManager, ERC6909Claims, Owned {
    using CurrencyLibrary for Currency;

    uint256 private _id = 1;

    mapping(Currency => mapping(PoolId => uint256)) private _poolTokenId;

    constructor(address initialOwner) Owned(initialOwner) {}

    function mint(uint256 id, uint256 amount) external {
        unchecked {
            _mint(msg.sender, id, amount);
        }
    }

    function burn(uint256 id, uint256 amount) external {
        unchecked {
            _burn(msg.sender, id, amount);
        }
    }

    function burnScale(uint256 id, uint256 total, uint256 amount) external {
        unchecked {
            uint256 burnAmount = amount * balanceOf[msg.sender][id] / total;
            _burn(msg.sender, id, burnAmount);
        }
    }
}
