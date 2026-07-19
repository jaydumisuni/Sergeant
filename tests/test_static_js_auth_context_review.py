from __future__ import annotations

from pathlib import Path

from main_review.static_js_auth_context_review import run_static_js_auth_context_review


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_use_auth_sign_in_direct_router_handoff_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "SignInForm.tsx"
    source.write_text(
        """
"use client";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function SignInForm() {
  const router = useRouter();
  const { signIn, signInWithGoogle } = useAuth();
  async function submit(email, password) {
    const verified = await signIn(email, password);
    router.replace(verified ? "/dashboard" : "/verify-email");
  }
  async function google() {
    await signInWithGoogle();
    router.replace("/dashboard");
  }
  return <form />;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_context_review(tmp_path, ["SignInForm.tsx"])

    assert "post-auth-navigation-before-router-cache-handoff" in _roots(result)


def test_use_auth_sign_in_dedicated_transition_helper_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "SignInForm.tsx"
    source.write_text(
        """
"use client";
import { startTransition } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function SignInForm() {
  const router = useRouter();
  const { signIn } = useAuth();
  function navigateAfterAuth(target) {
    startTransition(() => {
      router.refresh();
      router.replace(target);
    });
  }
  async function submit(email, password) {
    await signIn(email, password);
    navigateAfterAuth("/dashboard");
  }
  return <form />;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_context_review(tmp_path, ["SignInForm.tsx"])

    assert "post-auth-navigation-before-router-cache-handoff" not in _roots(result)


def test_non_auth_context_action_navigation_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "ProfileForm.tsx"
    source.write_text(
        """
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function ProfileForm() {
  const router = useRouter();
  const { updateProfile } = useAuth();
  async function submit(profile) {
    await updateProfile(profile);
    router.replace("/account");
  }
  return <form />;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_context_review(tmp_path, ["ProfileForm.tsx"])

    assert "post-auth-navigation-before-router-cache-handoff" not in _roots(result)


def _write_user_context(tmp_path: Path) -> None:
    (tmp_path / "UserContext.jsx").write_text(
        """
import { createContext, useContext, useEffect, useState } from "react";
import { getCurrentUser } from "@/services/userService";
const UserContext = createContext(null);
export function UserProvider({ children }) {
  const [user, setUser] = useState(null);
  async function refreshUser() {
    const currentUser = await getCurrentUser();
    setUser(currentUser);
  }
  useEffect(() => { refreshUser(); }, []);
  return <UserContext.Provider value={{ user, refreshUser }}>{children}</UserContext.Provider>;
}
export function useUser() { return useContext(UserContext); }
        """,
        encoding="utf-8",
    )
    (tmp_path / "Navbar.jsx").write_text(
        """
import { useUser } from "./UserContext";
export function Navbar() {
  const { user } = useUser();
  return <nav>{user ? user.email : "Login"}</nav>;
}
        """,
        encoding="utf-8",
    )


def test_token_write_navigation_before_user_context_refresh_is_reported(tmp_path: Path) -> None:
    _write_user_context(tmp_path)
    (tmp_path / "Login.jsx").write_text(
        """
import { login } from "./authService";
import { useNavigate } from "react-router-dom";
export function Login() {
  const navigate = useNavigate();
  async function submit(email, password) {
    const token = await login(email, password);
    localStorage.setItem("token", token.access_token);
    navigate("/dashboard");
  }
  return <form />;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_context_review(
        tmp_path,
        ["Login.jsx", "UserContext.jsx", "Navbar.jsx"],
    )

    assert "post-auth-navigation-before-user-context-refresh" in _roots(result)


def test_token_write_awaits_user_context_refresh_before_navigation(tmp_path: Path) -> None:
    _write_user_context(tmp_path)
    (tmp_path / "Login.jsx").write_text(
        """
import { login } from "./authService";
import { useUser } from "./UserContext";
import { useNavigate } from "react-router-dom";
export function Login() {
  const navigate = useNavigate();
  const { refreshUser } = useUser();
  async function submit(email, password) {
    const token = await login(email, password);
    localStorage.setItem("token", token.access_token);
    await refreshUser();
    navigate("/dashboard");
  }
  return <form />;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_context_review(
        tmp_path,
        ["Login.jsx", "UserContext.jsx", "Navbar.jsx"],
    )

    assert "post-auth-navigation-before-user-context-refresh" not in _roots(result)


def test_token_write_without_shared_user_context_is_clean(tmp_path: Path) -> None:
    (tmp_path / "Login.jsx").write_text(
        """
export async function loginAndLeave(token) {
  localStorage.setItem("token", token);
  navigate("/dashboard");
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_context_review(tmp_path, ["Login.jsx"])

    assert "post-auth-navigation-before-user-context-refresh" not in _roots(result)


def _write_sticky_session_query(tmp_path: Path, key: str = "session") -> None:
    (tmp_path / "use-user.ts").write_text(
        f"""
import {{ useQuery }} from "@tanstack/react-query";
const SESSION_QUERY_KEY = ["{key}"] as const;
const sessionQueryOptions = {{
  queryKey: SESSION_QUERY_KEY,
  queryFn: fetchSession,
  staleTime: 30 * 60 * 1000,
  refetchOnMount: false,
  retry: false,
}} as const;
export function useSession() {{ return useQuery(sessionQueryOptions); }}
        """,
        encoding="utf-8",
    )


def test_custom_next_router_navigates_before_session_query_invalidation(tmp_path: Path) -> None:
    _write_sticky_session_query(tmp_path)
    (tmp_path / "login-form.tsx").write_text(
        """
import { useRouter } from "@i18n/navigation";
import { login } from "@/features/auth/api";
export function LoginForm() {
  const router = useRouter();
  async function onSubmit(values) {
    await login(values.email, values.password);
    router.push("/dashboard");
  }
  return <form />;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_context_review(
        tmp_path,
        ["login-form.tsx", "use-user.ts"],
    )

    assert "post-auth-navigation-before-session-query-invalidation" in _roots(result)


def test_custom_next_router_invalidates_session_query_before_navigation(tmp_path: Path) -> None:
    _write_sticky_session_query(tmp_path)
    (tmp_path / "login-form.tsx").write_text(
        """
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "@i18n/navigation";
import { login } from "@/features/auth/api";
export function LoginForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  async function onSubmit(values) {
    await login(values.email, values.password);
    await queryClient.invalidateQueries({ queryKey: ["session"] });
    router.push("/dashboard");
  }
  return <form />;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_context_review(
        tmp_path,
        ["login-form.tsx", "use-user.ts"],
    )

    assert "post-auth-navigation-before-session-query-invalidation" not in _roots(result)


def test_non_session_query_does_not_create_auth_contract(tmp_path: Path) -> None:
    _write_sticky_session_query(tmp_path, key="projects")
    (tmp_path / "login-form.tsx").write_text(
        """
import { useRouter } from "@i18n/navigation";
import { login } from "@/features/auth/api";
export function LoginForm() {
  const router = useRouter();
  async function onSubmit(values) {
    await login(values.email, values.password);
    router.push("/dashboard");
  }
  return <form />;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_context_review(
        tmp_path,
        ["login-form.tsx", "use-user.ts"],
    )

    assert "post-auth-navigation-before-session-query-invalidation" not in _roots(result)
