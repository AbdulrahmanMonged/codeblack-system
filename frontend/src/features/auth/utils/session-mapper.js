export function mapAuthUserToSessionPayload(user) {
  if (!user) {
    return {
      user: null,
      roleIds: [],
      permissions: [],
      isOwner: false,
      isVerified: false,
    };
  }

  const isVerified = Boolean(user.is_verified);
  return {
    user: {
      userId: user.user_id,
      discordUserId: user.discord_user_id,
      username: user.username,
      avatarUrl: user.avatar_url || null,
      accountName: user.account_name || null,
      isVerified,
    },
    roleIds: user.role_ids ?? [],
    permissions: user.permissions ?? [],
    isOwner: Boolean(user.is_owner),
    isVerified,
  };
}
