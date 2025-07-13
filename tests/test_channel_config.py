#!/usr/bin/env python3
"""
Test script for channel exclusions and channel-specific rules functionality.
This script tests the new AI moderation channel configuration features.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cogs.aimod_helpers.config_manager import (
    get_excluded_channels,
    add_excluded_channel,
    remove_excluded_channel,
    is_channel_excluded,
    get_channel_rules,
    set_channel_rules,
    remove_channel_rules,
    get_all_channel_rules,
)

# Mock guild and channel IDs for testing
TEST_GUILD_ID = 123456789
TEST_CHANNEL_1 = 111111111
TEST_CHANNEL_2 = 222222222
TEST_CHANNEL_3 = 333333333


async def test_channel_exclusions():
    """Test channel exclusion functionality."""
    print("=== Testing Channel Exclusions ===")
    
    # Test 1: Initially no channels should be excluded
    excluded = await get_excluded_channels(TEST_GUILD_ID)
    print(f"Initial excluded channels: {excluded}")
    assert excluded == [], f"Expected empty list, got {excluded}"
    
    # Test 2: Add a channel to exclusions
    success = await add_excluded_channel(TEST_GUILD_ID, TEST_CHANNEL_1)
    print(f"Added channel {TEST_CHANNEL_1} to exclusions: {success}")
    assert success, "Failed to add channel to exclusions"
    
    # Test 3: Check if channel is excluded
    is_excluded = await is_channel_excluded(TEST_GUILD_ID, TEST_CHANNEL_1)
    print(f"Channel {TEST_CHANNEL_1} is excluded: {is_excluded}")
    assert is_excluded, "Channel should be excluded"
    
    # Test 4: Add another channel
    success = await add_excluded_channel(TEST_GUILD_ID, TEST_CHANNEL_2)
    print(f"Added channel {TEST_CHANNEL_2} to exclusions: {success}")
    assert success, "Failed to add second channel to exclusions"
    
    # Test 5: Get all excluded channels
    excluded = await get_excluded_channels(TEST_GUILD_ID)
    print(f"All excluded channels: {excluded}")
    assert TEST_CHANNEL_1 in excluded, "First channel should be in exclusions"
    assert TEST_CHANNEL_2 in excluded, "Second channel should be in exclusions"
    assert len(excluded) == 2, f"Expected 2 excluded channels, got {len(excluded)}"
    
    # Test 6: Try to add the same channel again (should still succeed)
    success = await add_excluded_channel(TEST_GUILD_ID, TEST_CHANNEL_1)
    print(f"Re-added channel {TEST_CHANNEL_1} to exclusions: {success}")
    assert success, "Re-adding channel should succeed"
    
    # Test 7: Check that we still have only 2 channels
    excluded = await get_excluded_channels(TEST_GUILD_ID)
    print(f"Excluded channels after re-add: {excluded}")
    assert len(excluded) == 2, f"Expected 2 excluded channels, got {len(excluded)}"
    
    # Test 8: Remove a channel from exclusions
    success = await remove_excluded_channel(TEST_GUILD_ID, TEST_CHANNEL_1)
    print(f"Removed channel {TEST_CHANNEL_1} from exclusions: {success}")
    assert success, "Failed to remove channel from exclusions"
    
    # Test 9: Check if channel is no longer excluded
    is_excluded = await is_channel_excluded(TEST_GUILD_ID, TEST_CHANNEL_1)
    print(f"Channel {TEST_CHANNEL_1} is excluded after removal: {is_excluded}")
    assert not is_excluded, "Channel should not be excluded after removal"
    
    # Test 10: Check remaining excluded channels
    excluded = await get_excluded_channels(TEST_GUILD_ID)
    print(f"Remaining excluded channels: {excluded}")
    assert TEST_CHANNEL_2 in excluded, "Second channel should still be excluded"
    assert len(excluded) == 1, f"Expected 1 excluded channel, got {len(excluded)}"
    
    print("✅ Channel exclusions tests passed!")


async def test_channel_rules():
    """Test channel-specific rules functionality."""
    print("\n=== Testing Channel-Specific Rules ===")
    
    # Test 1: Initially no custom rules
    rules = await get_channel_rules(TEST_GUILD_ID, TEST_CHANNEL_1)
    print(f"Initial rules for channel {TEST_CHANNEL_1}: '{rules}'")
    assert rules == "", f"Expected empty string, got '{rules}'"
    
    # Test 2: Set custom rules for a channel
    test_rules_1 = "1. Be family-friendly\n2. No swearing\n3. Keep it wholesome"
    success = await set_channel_rules(TEST_GUILD_ID, TEST_CHANNEL_1, test_rules_1)
    print(f"Set custom rules for channel {TEST_CHANNEL_1}: {success}")
    assert success, "Failed to set custom rules"
    
    # Test 3: Get the custom rules back
    rules = await get_channel_rules(TEST_GUILD_ID, TEST_CHANNEL_1)
    print(f"Retrieved rules for channel {TEST_CHANNEL_1}: '{rules[:50]}...'")
    assert rules == test_rules_1, f"Rules don't match. Expected '{test_rules_1}', got '{rules}'"
    
    # Test 4: Set rules for another channel
    test_rules_2 = "1. Adult content allowed\n2. NSFW discussions permitted\n3. Use content warnings"
    success = await set_channel_rules(TEST_GUILD_ID, TEST_CHANNEL_2, test_rules_2)
    print(f"Set custom rules for channel {TEST_CHANNEL_2}: {success}")
    assert success, "Failed to set custom rules for second channel"
    
    # Test 5: Get all channel rules
    all_rules = await get_all_channel_rules(TEST_GUILD_ID)
    print(f"All channel rules: {list(all_rules.keys())}")
    assert str(TEST_CHANNEL_1) in all_rules, "First channel should have custom rules"
    assert str(TEST_CHANNEL_2) in all_rules, "Second channel should have custom rules"
    assert len(all_rules) == 2, f"Expected 2 channels with rules, got {len(all_rules)}"
    
    # Test 6: Update existing rules
    updated_rules = "1. Be extra family-friendly\n2. No swearing at all\n3. Keep it super wholesome"
    success = await set_channel_rules(TEST_GUILD_ID, TEST_CHANNEL_1, updated_rules)
    print(f"Updated rules for channel {TEST_CHANNEL_1}: {success}")
    assert success, "Failed to update custom rules"
    
    # Test 7: Verify rules were updated
    rules = await get_channel_rules(TEST_GUILD_ID, TEST_CHANNEL_1)
    print(f"Updated rules for channel {TEST_CHANNEL_1}: '{rules[:50]}...'")
    assert rules == updated_rules, f"Rules weren't updated correctly"
    
    # Test 8: Remove custom rules
    success = await remove_channel_rules(TEST_GUILD_ID, TEST_CHANNEL_1)
    print(f"Removed custom rules for channel {TEST_CHANNEL_1}: {success}")
    assert success, "Failed to remove custom rules"
    
    # Test 9: Verify rules were removed
    rules = await get_channel_rules(TEST_GUILD_ID, TEST_CHANNEL_1)
    print(f"Rules after removal for channel {TEST_CHANNEL_1}: '{rules}'")
    assert rules == "", f"Expected empty string after removal, got '{rules}'"
    
    # Test 10: Check that other channel still has rules
    rules = await get_channel_rules(TEST_GUILD_ID, TEST_CHANNEL_2)
    print(f"Rules for channel {TEST_CHANNEL_2} after other removal: '{rules[:50]}...'")
    assert rules == test_rules_2, "Other channel's rules should be unchanged"
    
    # Test 11: Get all rules again
    all_rules = await get_all_channel_rules(TEST_GUILD_ID)
    print(f"All channel rules after removal: {list(all_rules.keys())}")
    assert str(TEST_CHANNEL_1) not in all_rules, "First channel should not have custom rules"
    assert str(TEST_CHANNEL_2) in all_rules, "Second channel should still have custom rules"
    assert len(all_rules) == 1, f"Expected 1 channel with rules, got {len(all_rules)}"
    
    print("✅ Channel-specific rules tests passed!")


async def cleanup():
    """Clean up test data."""
    print("\n=== Cleaning Up Test Data ===")
    
    # Remove all excluded channels
    await remove_excluded_channel(TEST_GUILD_ID, TEST_CHANNEL_1)
    await remove_excluded_channel(TEST_GUILD_ID, TEST_CHANNEL_2)
    await remove_excluded_channel(TEST_GUILD_ID, TEST_CHANNEL_3)
    
    # Remove all custom rules
    await remove_channel_rules(TEST_GUILD_ID, TEST_CHANNEL_1)
    await remove_channel_rules(TEST_GUILD_ID, TEST_CHANNEL_2)
    await remove_channel_rules(TEST_GUILD_ID, TEST_CHANNEL_3)
    
    print("✅ Cleanup completed!")


async def main():
    """Run all tests."""
    print("Starting AI Channel Configuration Tests...")
    print("=" * 50)
    
    try:
        await test_channel_exclusions()
        await test_channel_rules()
        await cleanup()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed successfully!")
        print("Channel exclusions and channel-specific rules are working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        await cleanup()
        sys.exit(1)


if __name__ == "__main__":
    # Note: This test requires the database to be initialized
    # In a real environment, you would need to set up the database connection first
    print("⚠️  Note: This test requires a database connection to be available.")
    print("Make sure the bot's database is initialized before running this test.")
    print("For now, this is a dry-run showing the test structure.")
    
    # Uncomment the line below to run actual tests (requires database)
    # asyncio.run(main())
