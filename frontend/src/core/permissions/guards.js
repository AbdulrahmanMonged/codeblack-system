export function hasPermissionSet(requiredPermissions, ownedPermissions, isOwner) {
  if (isOwner) {
    return true;
  }

  if (!requiredPermissions || requiredPermissions.length === 0) {
    return true;
  }

  const owned = new Set(ownedPermissions || []);
  return requiredPermissions.every((permission) => owned.has(permission));
}

export function hasAnyPermissionSet(requiredPermissions, ownedPermissions, isOwner) {
  if (isOwner) {
    return true;
  }

  if (!requiredPermissions || requiredPermissions.length === 0) {
    return true;
  }

  const owned = new Set(ownedPermissions || []);
  return requiredPermissions.some((permission) => owned.has(permission));
}
