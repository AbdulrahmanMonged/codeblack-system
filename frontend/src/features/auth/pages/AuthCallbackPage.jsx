import { Button, Card, Spinner } from "@heroui/react";
import { CheckCircle2, RefreshCw, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "../../../shared/ui/toast.jsx";
import { useAppDispatch, useAppSelector } from "../../../app/store/hooks.js";
import {
  hydrationCompleted,
  hydrationFailed,
  selectSessionStatus,
} from "../../../app/store/slices/sessionSlice.js";
import { createDiscordLogin, exchangeDiscordCallback } from "../api/auth-api.js";
import { mapAuthUserToSessionPayload } from "../utils/session-mapper.js";

const callbackExchangePromises = new Map();
const CALLBACK_PROMISE_CACHE_TTL_MS = 60_000;
const CALLBACK_EXCHANGE_TIMEOUT_MS = 20_000;

function getOrCreateCallbackExchangePromise({ code, state }) {
  const key = `${code}:${state}`;
  const existingPromise = callbackExchangePromises.get(key);
  if (existingPromise) {
    return existingPromise;
  }

  const promise = exchangeDiscordCallback({ code, state })
    .finally(() => {
      window.setTimeout(() => {
        callbackExchangePromises.delete(key);
      }, CALLBACK_PROMISE_CACHE_TTL_MS);
    });

  callbackExchangePromises.set(key, promise);
  return promise;
}

async function withCallbackTimeout(promise) {
  let timeoutId = null;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timeoutId = window.setTimeout(() => {
          reject(new Error("Discord callback timed out. Please try signing in again."));
        }, CALLBACK_EXCHANGE_TIMEOUT_MS);
      }),
    ]);
  } finally {
    if (timeoutId) {
      window.clearTimeout(timeoutId);
    }
  }
}

export function AuthCallbackPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionStatus = useAppSelector(selectSessionStatus);
  const [state, setState] = useState({ loading: true, error: "" });
  const [isRetryingSignIn, setIsRetryingSignIn] = useState(false);

  const code = useMemo(() => searchParams.get("code") || "", [searchParams]);
  const oauthState = useMemo(() => searchParams.get("state") || "", [searchParams]);
  const callbackKey = useMemo(() => `${code}:${oauthState}`, [code, oauthState]);

  useEffect(() => {
    let cancelled = false;

    async function processCallback() {
      if (!code || !oauthState) {
        dispatch(hydrationFailed());
        setState({
          loading: false,
          error: "Missing OAuth callback parameters. Restart the sign-in flow.",
        });
        return;
      }

      try {
        const payload = await withCallbackTimeout(
          getOrCreateCallbackExchangePromise({
            code,
            state: oauthState,
          }),
        );
        if (cancelled) {
          return;
        }

        dispatch(hydrationCompleted(mapAuthUserToSessionPayload(payload?.user)));
        setState({ loading: false, error: "" });
        toast.success("Authentication completed");
        navigate("/dashboard", { replace: true });
      } catch (error) {
        if (cancelled) {
          return;
        }
        dispatch(hydrationFailed());
        setState({
          loading: false,
          error: error?.message || "Discord callback failed",
        });
      }
    }

    processCallback();

    return () => {
      cancelled = true;
    };
  }, [callbackKey, code, oauthState, dispatch, navigate]);

  if (sessionStatus === "authenticated" && !state.loading && !state.error) {
    return null;
  }

  async function handleRetrySignIn() {
    setIsRetryingSignIn(true);
    try {
      const payload = await createDiscordLogin({ nextUrl: "/dashboard" });
      if (!payload?.authorize_url) {
        throw new Error("Missing Discord authorize URL");
      }
      window.location.assign(payload.authorize_url);
    } catch (error) {
      toast.error(error?.message || "Failed to restart Discord sign-in");
      setIsRetryingSignIn(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-2xl">
      <Card className="border border-white/15 bg-black/55 shadow-2xl backdrop-blur-xl">
        <Card.Header className="space-y-2 p-7">
          <Card.Title className="cb-feature-title text-3xl">Discord Callback</Card.Title>
          <Card.Description className="text-white/80">
            Finalizing your CodeBlack session and loading role permissions.
          </Card.Description>
        </Card.Header>
        <Card.Content className="space-y-5 px-7 pb-7">
          {state.loading ? (
            <div className="flex items-center gap-3 rounded-xl border border-white/15 bg-white/5 p-4">
              <Spinner size="sm" />
              <p className="text-sm text-white/80">Verifying OAuth state and creating session...</p>
            </div>
          ) : null}

          {!state.loading && !state.error ? (
            <div className="flex items-center gap-3 rounded-xl border border-emerald-300/25 bg-emerald-300/10 p-4 text-emerald-100">
              <CheckCircle2 size={16} />
              <p className="text-sm">Authentication completed. Redirecting to dashboard.</p>
            </div>
          ) : null}

          {state.error ? (
            <div className="space-y-4">
              <div className="flex items-start gap-3 rounded-xl border border-rose-300/25 bg-rose-300/10 p-4 text-rose-100">
                <TriangleAlert size={16} className="mt-0.5" />
                <p className="text-sm">{state.error}</p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Button
                  color="warning"
                  isLoading={isRetryingSignIn}
                  isDisabled={isRetryingSignIn}
                  startContent={<RefreshCw size={15} />}
                  onPress={handleRetrySignIn}
                >
                  Try Sign-In Again
                </Button>
                <Button as={Link} to="/" variant="ghost">
                  Return Home
                </Button>
              </div>
            </div>
          ) : null}
        </Card.Content>
      </Card>
    </div>
  );
}
