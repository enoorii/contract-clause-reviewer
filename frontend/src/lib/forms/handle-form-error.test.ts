import { describe, it, expect, vi } from "vitest";
import type { UseFormReturn } from "react-hook-form";
import { handleFormError } from "./handle-form-error";
import { HttpError, NetworkError } from "@/lib/api/types";

type TestFormValues = Record<string, string>;

function makeForm(fieldNames: string[]): UseFormReturn<TestFormValues> {
  const values: TestFormValues = Object.fromEntries(
    fieldNames.map((name) => [name, ""]),
  );
  return {
    getValues: () => values,
    setError: vi.fn(),
  } as unknown as UseFormReturn<TestFormValues>;
}

describe("handleFormError", () => {
  it("calls setFormError for a NetworkError", () => {
    const form = makeForm(["a"]);
    const setFormError = vi.fn();

    handleFormError(new NetworkError("Offline"), {
      form,
      setFormError,
      fallback: "fallback",
    });

    expect(setFormError).toHaveBeenCalledWith("Offline");
    expect(form.setError).not.toHaveBeenCalled();
  });

  it("calls setFormError for an unknown error", () => {
    const form = makeForm(["a"]);
    const setFormError = vi.fn();

    handleFormError(new Error("boom"), {
      form,
      setFormError,
      fallback: "fallback",
    });

    expect(setFormError).toHaveBeenCalledWith("An unexpected error occurred.");
  });

  it("maps 422 field errors via fieldMap", () => {
    const form = makeForm(["oldPassword", "newPassword"]);
    const setFormError = vi.fn();

    handleFormError(
      new HttpError(422, "Validation failed", [
        { loc: ["body", "old_password"], msg: "Required", type: "missing" },
      ]),
      {
        form,
        fieldMap: { old_password: "oldPassword" },
        setFormError,
        fallback: "fallback",
      },
    );

    expect(form.setError).toHaveBeenCalledWith("oldPassword", {
      type: "server",
      message: "Required",
    });
    expect(setFormError).not.toHaveBeenCalled();
  });

  it("falls back to setFormError when a 422 field is unknown to the form", () => {
    const form = makeForm(["username"]);
    const setFormError = vi.fn();

    handleFormError(
      new HttpError(422, "Validation failed", [
        { loc: ["body", "unknown_field"], msg: "Bad", type: "value_error" },
      ]),
      { form, setFormError, fallback: "fallback" },
    );

    expect(setFormError).toHaveBeenCalledWith("Bad");
    expect(form.setError).not.toHaveBeenCalled();
  });

  it("calls setFormError for a string detail on non-422 errors", () => {
    const form = makeForm(["a"]);
    const setFormError = vi.fn();

    handleFormError(new HttpError(400, "Bad request", "Business rule failed"), {
      form,
      setFormError,
      fallback: "fallback",
    });

    expect(setFormError).toHaveBeenCalledWith("Business rule failed");
  });

  it("uses err.message as a last resort", () => {
    const form = makeForm(["a"]);
    const setFormError = vi.fn();

    handleFormError(new HttpError(500, "Server exploded"), {
      form,
      setFormError,
      fallback: "fallback",
    });

    expect(setFormError).toHaveBeenCalledWith("Server exploded");
  });
});
