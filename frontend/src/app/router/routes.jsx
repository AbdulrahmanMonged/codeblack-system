import { createBrowserRouter } from "react-router-dom";
import { RequireAuth } from "./RequireAuth.jsx";
import { RequirePermission } from "./RequirePermission.jsx";
import { RequireVerified } from "./RequireVerified.jsx";
import { ParamFeaturePage } from "./route-elements.jsx";
import { AdminDashboardPage } from "../../features/admin/pages/AdminDashboardPage.jsx";
import { AuditTimelinePage } from "../../features/admin/pages/AuditTimelinePage.jsx";
import { ReviewQueuePage } from "../../features/admin/pages/ReviewQueuePage.jsx";
import { ApplicationEligibilityPage } from "../../features/applications/pages/ApplicationEligibilityPage.jsx";
import { ApplicationsPage } from "../../features/applications/pages/ApplicationsPage.jsx";
import { ApplicationSubmitPage } from "../../features/applications/pages/ApplicationSubmitPage.jsx";
import { ActivitiesPage } from "../../features/activities/pages/ActivitiesPage.jsx";
import { ActivityDetailPage } from "../../features/activities/pages/ActivityDetailPage.jsx";
import { AuthCallbackPage } from "../../features/auth/pages/AuthCallbackPage.jsx";
import { BlacklistManagementPage } from "../../features/blacklist/pages/BlacklistManagementPage.jsx";
import { BlacklistRemovalRequestPage } from "../../features/blacklist/pages/BlacklistRemovalRequestPage.jsx";
import { BotControlPage } from "../../features/bot-control/pages/BotControlPage.jsx";
import { ConfigRegistryPage } from "../../features/config-registry/pages/ConfigRegistryPage.jsx";
import { NotificationsCenterPage } from "../../features/notifications/pages/NotificationsCenterPage.jsx";
import { OrderSubmitPage } from "../../features/orders/pages/OrderSubmitPage.jsx";
import { RoleMatrixPage } from "../../features/permissions/pages/RoleMatrixPage.jsx";
import { PlayerbasePage } from "../../features/playerbase/pages/PlayerbasePage.jsx";
import { PostsManagementPage } from "../../features/posts/pages/PostsManagementPage.jsx";
import { PublicRosterPage } from "../../features/roster/pages/PublicRosterPage.jsx";
import { RosterManagementPage } from "../../features/roster/pages/RosterManagementPage.jsx";
import { VacationsPage } from "../../features/vacations/pages/VacationsPage.jsx";
import { VerifyAccountPage } from "../../features/verification/pages/VerifyAccountPage.jsx";
import { VotingContextPage } from "../../features/voting/pages/VotingContextPage.jsx";
import { LandingPage } from "../../features/home/pages/LandingPage.jsx";
import { AppShell } from "../../shared/layout/AppShell.jsx";
import { PublicLayout } from "../../shared/layout/PublicLayout.jsx";
import { RootLayout } from "../../shared/layout/RootLayout.jsx";
import { NotFoundPage } from "../../shared/ui/NotFoundPage.jsx";

export const appRouter = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        element: <PublicLayout />,
        children: [
          { index: true, element: <LandingPage /> },
          {
            path: "auth/callback",
            element: <AuthCallbackPage />,
          },
          {
            path: "applications/new",
            element: <ApplicationSubmitPage />,
          },
          {
            path: "applications/eligibility",
            element: <ApplicationEligibilityPage />,
          },
          {
            path: "blacklist/removal-request",
            element: <BlacklistRemovalRequestPage />,
          },
          {
            path: "roster-public",
            element: <PublicRosterPage />,
          },
        ],
      },
      {
        path: "verify-account",
        element: (
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        ),
        children: [
          {
            index: true,
            element: <VerifyAccountPage />,
          },
        ],
      },
      {
        element: (
          <RequireAuth>
            <RequireVerified>
              <AppShell />
            </RequireVerified>
          </RequireAuth>
        ),
        children: [
          {
            path: "dashboard",
            element: <AdminDashboardPage />,
          },
          {
            path: "notifications",
            element: <NotificationsCenterPage />,
          },
          {
            path: "applications",
            element: <ApplicationsPage />,
          },
          {
            path: "applications/:publicId",
            element: <ApplicationsPage />,
          },
          {
            path: "orders",
            element: <OrderSubmitPage />,
          },
          {
            path: "orders/:publicId",
            element: (
              <ParamFeaturePage
                title="Order Details"
                description="Order-specific status, decisions, and moderation notes."
                endpointHintBuilder={(params) =>
                  `/api/v1/orders/${params.publicId || "{public_id}"}`
                }
              />
            ),
          },
          {
            path: "roster",
            element: <RosterManagementPage />,
          },
          {
            path: "playerbase",
            element: <PlayerbasePage />,
          },
          {
            path: "blacklist",
            element: <BlacklistManagementPage />,
          },
          {
            path: "activities",
            element: <ActivitiesPage />,
          },
          {
            path: "activities/:publicId",
            element: <ActivityDetailPage />,
          },
          {
            path: "vacations",
            element: <VacationsPage />,
          },
          {
            path: "posts",
            element: <PostsManagementPage />,
          },
          {
            path: "voting/:contextType/:contextId",
            element: <VotingContextPage />,
          },
          {
            path: "voting/application/:applicationId",
            element: <VotingContextPage />,
          },
          {
            path: "admin/review-queue",
            element: (
              <RequirePermission
                mode="any"
                requiredPermissions={[
                  "applications.review",
                  "orders.review",
                  "blacklist_removal_requests.review",
                  "activities.approve",
                  "vacations.approve",
                  "verification_requests.review",
                ]}
                fallbackDescription="You need reviewer-level permissions to access review queue."
              >
                <ReviewQueuePage />
              </RequirePermission>
            ),
          },
          {
            path: "admin/audit",
            element: (
              <RequirePermission
                requiredPermissions={["audit.read"]}
                fallbackDescription="You need audit.read permission to access audit timeline."
              >
                <AuditTimelinePage />
              </RequirePermission>
            ),
          },
          {
            path: "permissions/role-matrix",
            element: (
              <RequirePermission
                requiredPermissions={["discord_role_permissions.read"]}
                fallbackDescription="You need discord_role_permissions.read permission to view role matrix."
              >
                <RoleMatrixPage />
              </RequirePermission>
            ),
          },
          {
            path: "config/registry",
            element: (
              <RequirePermission
                requiredPermissions={["config_registry.read"]}
                fallbackDescription="You need config_registry.read permission to access configuration registry."
              >
                <ConfigRegistryPage />
              </RequirePermission>
            ),
          },
          {
            path: "bot/control",
            element: (
              <RequirePermission
                requiredPermissions={["bot.read_status"]}
                fallbackDescription="You need bot.read_status permission to access bot controls."
              >
                <BotControlPage />
              </RequirePermission>
            ),
          },
        ],
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
