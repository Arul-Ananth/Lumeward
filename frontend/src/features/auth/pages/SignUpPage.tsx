import * as React from "react";
import { useNavigate } from "react-router-dom";

import AuthSplitLayout from "../../../components/AuthSplitLayout";
import { useAuth } from "../../../hooks/useAuth";
import AuthFormScaffold, {
  AuthTextField,
} from "../components/AuthFormScaffold";

export default function SignUpPage() {
  const navigate = useNavigate();
  const { signupOrganization } = useAuth();
  const [organizationName, setOrganizationName] = React.useState("");
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [nameError, setNameError] = React.useState("");
  const [emailError, setEmailError] = React.useState("");
  const [passwordError, setPasswordError] = React.useState("");
  const [formError, setFormError] = React.useState("");
  const [organizationError, setOrganizationError] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  const validateInputs = () => {
    let valid = true;
    if (!organizationName.trim()) {
      setOrganizationError("Organization name is required.");
      valid = false;
    } else setOrganizationError("");
    if (!name.trim()) {
      setNameError("Name is required.");
      valid = false;
    } else {
      setNameError("");
    }
    if (!email || !/\S+@\S+\.\S+/.test(email)) {
      setEmailError("Please enter a valid email address.");
      valid = false;
    } else {
      setEmailError("");
    }
    if (!password || password.length < 8) {
      setPasswordError("Password must be at least 8 characters long.");
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
      await signupOrganization(name, email, password, organizationName);
      navigate("/onboarding/workspace");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setFormError(`Signup failed: ${message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthSplitLayout
      heroTitle="Create your organization workspace."
      heroBody="Set up Lumeward for your team. Your organization is activated immediately, and you can create its first workspace next."
      heroTags={["Immediate setup", "Organization admin", "Team-ready"]}
    >
      <AuthFormScaffold
        alternateHref="/signin"
        alternatePrompt="Already have an account?"
        alternateText="Sign in"
        formError={formError}
        onSubmit={handleSubmit}
        submitting={submitting}
        submitText="Create organization"
        title="Create your organization"
      >
        <AuthTextField
          error={Boolean(organizationError)}
          helperText={organizationError}
          id="organization"
          label="Organization name"
          value={organizationName}
          onChange={(event) => setOrganizationName(event.target.value)}
          autoFocus
        />
        <AuthTextField
          error={Boolean(nameError)}
          helperText={nameError}
          id="name"
          label="Name"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <AuthTextField
          error={Boolean(emailError)}
          helperText={emailError}
          id="email"
          label="Email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <AuthTextField
          error={Boolean(passwordError)}
          helperText={passwordError}
          id="password"
          label="Password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </AuthFormScaffold>
    </AuthSplitLayout>
  );
}
