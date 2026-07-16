import * as React from "react";
import { useNavigate } from "react-router-dom";

import AuthSplitLayout from "../../../components/AuthSplitLayout";
import { useAuth } from "../../../hooks/useAuth";
import AuthFormScaffold, {
  AuthTextField,
} from "../components/AuthFormScaffold";

export default function SignInPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [emailError, setEmailError] = React.useState("");
  const [passwordError, setPasswordError] = React.useState("");
  const [formError, setFormError] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  const validateInputs = () => {
    let valid = true;
    if (!email || !/\S+@\S+\.\S+/.test(email)) {
      setEmailError("Please enter a valid email address.");
      valid = false;
    } else {
      setEmailError("");
    }
    if (!password) {
      setPasswordError("Password is required.");
      valid = false;
    } else {
      setPasswordError("");
    }
    return valid;
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError("");
    if (!validateInputs()) {
      return;
    }

    try {
      setSubmitting(true);
      await login(email, password);
      navigate("/");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setFormError(`Sign in failed: ${message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthSplitLayout
      heroTitle="Your organization, clearly organized."
      heroBody="Sign in to manage people, workspaces, and shared knowledge, or continue to your personal workspace."
      heroTags={["People", "Workspaces", "Shared context"]}
    >
      <AuthFormScaffold
        alternateHref="/signup"
        alternatePrompt="Don't have an account?"
        alternateText="Sign up"
        formError={formError}
        onSubmit={handleSubmit}
        submitting={submitting}
        submitText="Sign in"
        title="Sign in"
      >
        <AuthTextField
          error={Boolean(emailError)}
          helperText={emailError}
          id="email"
          label="Email"
          type="email"
          placeholder="you@domain.com"
          autoComplete="email"
          autoFocus
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <AuthTextField
          error={Boolean(passwordError)}
          helperText={passwordError}
          id="password"
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </AuthFormScaffold>
    </AuthSplitLayout>
  );
}
