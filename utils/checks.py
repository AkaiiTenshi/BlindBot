from discord import Interaction

from utils.data_manager import DataManager


async def has_admin_role(interaction: Interaction) -> bool:
    config = DataManager().load_config()
    admin_role_id = config.get("admin_role_id")
    if interaction.user.guild_permissions.manage_channels:
        return True
    if admin_role_id is not None and any(role.id == admin_role_id for role in interaction.user.roles):
        return True
    await interaction.response.send_message(
        "❌ You don't have permission to use this command.", ephemeral=True
    )
    return False
