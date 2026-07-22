from __future__ import annotations

from pathlib import Path

from main_review.static_js_auth_transition_review import (
    run_static_js_auth_transition_review,
)


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_navbar_plain_browser_config_read_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "navbar.jsx"
    source.write_text(
        """
import { useEffect, useState } from "react";

function getCachedConfig() {
  return JSON.parse(localStorage.getItem("config") || "{}");
}

export default function Navbar() {
  const [customAvatar, setCustomAvatar] = useState("");
  const config = getCachedConfig();
  const authMode = config?.settings?.auth?.mode || "local";
  const accountName = config?.settings?.auth?.jellyfinUser?.name || config?.username;
  return <div className="account"><span>{accountName}</span><small>{authMode}</small></div>;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_transition_review(tmp_path, ["navbar.jsx"])

    assert "browser-auth-cache-read-without-reactive-owner" in _roots(result)


def test_navbar_mount_state_without_external_invalidation_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "navbar.jsx"
    source.write_text(
        """
import { useState } from "react";

function getCachedConfig() {
  return JSON.parse(localStorage.getItem("account_config") || "{}");
}

export default function Navbar() {
  const [config, setConfig] = useState(() => getCachedConfig());
  return <div>{config?.auth?.user?.name || "sign in"}</div>;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_transition_review(tmp_path, ["navbar.jsx"])

    assert "browser-auth-cache-read-without-reactive-owner" in _roots(result)


def test_navbar_state_with_config_event_refresh_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "navbar.jsx"
    source.write_text(
        """
import { useEffect, useState } from "react";

function getCachedConfig() {
  return JSON.parse(localStorage.getItem("config") || "{}");
}

export default function Navbar() {
  const [config, setConfig] = useState(() => getCachedConfig());
  useEffect(() => {
    const refreshConfig = () => setConfig(getCachedConfig());
    window.addEventListener("account-config-updated", refreshConfig);
    window.addEventListener("storage", refreshConfig);
    return () => {
      window.removeEventListener("account-config-updated", refreshConfig);
      window.removeEventListener("storage", refreshConfig);
    };
  }, []);
  return <div>{config?.auth?.user?.name || "sign in"}</div>;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_transition_review(tmp_path, ["navbar.jsx"])

    assert "browser-auth-cache-read-without-reactive-owner" not in _roots(result)


def test_non_chrome_browser_cache_reader_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "settings.jsx"
    source.write_text(
        """
function getCachedConfig() {
  return JSON.parse(localStorage.getItem("config") || "{}");
}

export default function SettingsPanel() {
  const config = getCachedConfig();
  return <pre>{JSON.stringify(config)}</pre>;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_transition_review(tmp_path, ["settings.jsx"])

    assert "browser-auth-cache-read-without-reactive-owner" not in _roots(result)


def test_next_login_soft_navigation_without_refresh_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "LoginForm.tsx"
    source.write_text(
        """
"use client";
import { loginAction } from "@/app/login/_action";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

const LoginForm = () => {
  const router = useRouter();
  const { mutateAsync } = useMutation({
    mutationFn: (payload) => loginAction(payload),
  });
  const submit = async (value) => {
    const result = await mutateAsync(value);
    if (!result.success) return;
    router.push("/dashboard");
  };
  return <form />;
};
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_transition_review(tmp_path, ["LoginForm.tsx"])

    assert "post-auth-navigation-without-server-tree-refresh" in _roots(result)


def test_next_login_refresh_before_navigation_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "LoginForm.tsx"
    source.write_text(
        """
"use client";
import { loginAction } from "@/app/login/_action";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

const LoginForm = () => {
  const router = useRouter();
  const { mutateAsync } = useMutation({
    mutationFn: (payload) => loginAction(payload),
  });
  const submit = async (value) => {
    const result = await mutateAsync(value);
    if (!result.success) return;
    router.refresh();
    router.push("/dashboard");
  };
  return <form />;
};
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_transition_review(tmp_path, ["LoginForm.tsx"])

    assert "post-auth-navigation-without-server-tree-refresh" not in _roots(result)


def test_next_login_query_invalidation_before_navigation_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "LoginForm.tsx"
    source.write_text(
        """
"use client";
import { loginAction } from "@/app/login/_action";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

const LoginForm = () => {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { mutateAsync } = useMutation({
    mutationFn: (payload) => loginAction(payload),
  });
  const submit = async (value) => {
    await mutateAsync(value);
    await queryClient.invalidateQueries({ queryKey: ["session"] });
    router.replace("/dashboard");
  };
  return <form />;
};
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_transition_review(tmp_path, ["LoginForm.tsx"])

    assert "post-auth-navigation-without-server-tree-refresh" not in _roots(result)


def test_unrelated_next_mutation_and_navigation_are_clean(tmp_path: Path) -> None:
    source = tmp_path / "ProjectForm.tsx"
    source.write_text(
        """
"use client";
import { saveProject } from "@/projects/actions";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

export function ProjectForm() {
  const router = useRouter();
  const { mutateAsync } = useMutation({ mutationFn: saveProject });
  const submit = async (project) => {
    await mutateAsync(project);
    router.push("/projects");
  };
  return <form />;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_transition_review(tmp_path, ["ProjectForm.tsx"])

    assert "post-auth-navigation-without-server-tree-refresh" not in _roots(result)


def test_supabase_login_navigation_before_session_sync_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "Auth.tsx"
    source.write_text(
        """
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";

export default function Auth() {
  const navigate = useNavigate();
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) navigate("/dashboard", { replace: true });
    });
  }, [navigate]);

  async function handleSubmit(email, password) {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return;
    navigate("/dashboard", { replace: true });
  }
  return <form />;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_transition_review(tmp_path, ["Auth.tsx"])

    assert "post-auth-navigation-before-session-cache-refresh" in _roots(result)


def test_supabase_login_query_invalidation_before_navigation_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "Auth.tsx"
    source.write_text(
        """
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export default function Auth() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) navigate("/dashboard", { replace: true });
    });
  }, [navigate]);

  async function handleSubmit(email, password) {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return;
    await queryClient.invalidateQueries({ queryKey: ["session"] });
    navigate("/dashboard", { replace: true });
  }
  return <form />;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_transition_review(tmp_path, ["Auth.tsx"])

    assert "post-auth-navigation-before-session-cache-refresh" not in _roots(result)


def test_supabase_sign_in_without_shared_session_consumer_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "Auth.tsx"
    source.write_text(
        """
import { useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";

export default function Auth() {
  const navigate = useNavigate();
  async function handleSubmit(email, password) {
    await supabase.auth.signInWithPassword({ email, password });
    navigate("/dashboard");
  }
  return <form />;
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_auth_transition_review(tmp_path, ["Auth.tsx"])

    assert "post-auth-navigation-before-session-cache-refresh" not in _roots(result)
