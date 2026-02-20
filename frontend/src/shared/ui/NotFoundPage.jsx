import { Button, Card } from "@heroui/react";
import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-2xl items-center px-4 py-10">
      <Card className="w-full border border-white/15 bg-black/50 p-6 shadow-2xl backdrop-blur-xl">
        <Card.Header className="space-y-2">
          <Card.Title className="cb-feature-title text-4xl">404</Card.Title>
          <Card.Description className="text-white/75">
            This route is not mapped yet.
          </Card.Description>
        </Card.Header>
        <Card.Content className="pt-4">
          <Button as={Link} to="/dashboard" color="warning">
            Return to dashboard
          </Button>
        </Card.Content>
      </Card>
    </div>
  );
}
