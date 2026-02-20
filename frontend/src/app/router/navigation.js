export const APP_NAV_SECTIONS = [
  {
    title: "Operations",
    items: [
      { to: "/dashboard", label: "Dashboard" },
      {
        to: "/applications",
        label: "Applications",
        requiredAny: ["applications.read_public", "applications.read_private"],
      },
      { to: "/orders", label: "Orders", requiredAny: ["orders.read", "orders.submit"] },
      { to: "/activities", label: "Activities", requiredAny: ["activities.read", "activities.create"] },
      { to: "/vacations", label: "Vacations", requiredAny: ["vacations.read", "vacations.submit"] },
      { to: "/posts", label: "Posts", requiredAny: ["posts.read", "posts.write", "posts.publish"] },
    ],
  },
  {
    title: "Roster",
    items: [
      { to: "/roster", label: "Roster", requiredAny: ["roster.read", "roster.write"] },
      { to: "/playerbase", label: "Playerbase", requiredAny: ["playerbase.read", "playerbase.write"] },
      { to: "/blacklist", label: "Blacklist", requiredAny: ["blacklist.read", "blacklist.add"] },
      { to: "/notifications", label: "Notifications", requiredAny: ["notifications.read"] },
    ],
  },
  {
    title: "Staff",
    items: [
      {
        to: "/admin/review-queue",
        label: "Review Queue",
        requiredAny: [
          "applications.review",
          "orders.review",
          "blacklist_removal_requests.review",
          "activities.approve",
          "vacations.approve",
          "verification_requests.review",
        ],
      },
      { to: "/admin/audit", label: "Audit Timeline", requiredAny: ["audit.read"] },
      {
        to: "/permissions/role-matrix",
        label: "Role Matrix",
        requiredAny: ["discord_role_permissions.read"],
      },
      { to: "/config/registry", label: "Config Registry", requiredAny: ["config_registry.read"] },
      { to: "/bot/control", label: "Bot Control", requiredAny: ["bot.read_status"] },
    ],
  },
];
