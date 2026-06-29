"""
Permission checking decorators for Blindy2 admin commands.

This module provides permission checks to ensure only authorized users
can use admin commands.
"""

from discord import Interaction


async def has_manage_channels(interaction: Interaction) -> bool:
    """
    Check if the user has the 'Manage Channels' permission.

    This is used as a decorator for admin commands to ensure only users
    with appropriate permissions can use them.

    Args:
        interaction: Discord interaction object from the command

    Returns:
        True if user has permission, False otherwise
        (Also sends an error message to the user if they don't have permission)
    """
    if interaction.user.guild_permissions.manage_channels:
        return True
    else:
        await interaction.response.send_message(
            "❌ You need 'Manage Channels' permission to use this command.",
            ephemeral=True,
        )
        return False
