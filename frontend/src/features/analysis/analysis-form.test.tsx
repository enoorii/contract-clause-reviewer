import { describe, it, expect, beforeEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router";

import { renderWithProviders } from "@/tests/test-utils";
import { HttpError } from "@/lib/api/types";

vi.mock("./api", () => ({
  submitAnalysis: vi.fn(),
}));

import * as analysisApi from "./api";
import { AnalysisForm } from "./analysis-form";

function renderTree() {
  return renderWithProviders(
    <Routes>
      <Route path="/" element={<AnalysisForm />} />
      <Route path="/analysis/status/:taskId" element={<div>Status page</div>} />
    </Routes>,
  );
}

describe("AnalysisForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all form fields", () => {
    renderTree();
    expect(screen.getByLabelText(/contract title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contract text/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
  });

  it("keeps submit disabled while invalid", () => {
    renderTree();
    expect(
      screen.getByRole("button", { name: /start analysis/i }),
    ).toBeDisabled();
  });

  it("shows a validation error for short text after blur", async () => {
    const user = userEvent.setup();
    renderTree();

    await user.type(screen.getByLabelText(/contract text/i), "short");
    await user.tab();

    expect(
      await screen.findByText(/contract text must be at least 10 characters/i),
    ).toBeInTheDocument();
  });

  it("submits valid data and navigates to the status page", async () => {
    const user = userEvent.setup();
    vi.mocked(analysisApi.submitAnalysis).mockResolvedValue({
      task_id: "task-abc",
    });

    renderTree();

    await user.type(
      screen.getByLabelText("Contract Title", { exact: true }),
      "Service Agreement",
    );
    await user.type(
      screen.getByLabelText("Contract Text", { exact: true }),
      "The parties hereby agree to the following terms and conditions.",
    );

    const submitButton = screen.getByRole("button", {
      name: /start analysis/i,
    });
    await waitFor(() => expect(submitButton).toBeEnabled());
    await user.click(submitButton);

    await waitFor(() =>
      expect(analysisApi.submitAnalysis).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Service Agreement",
          text: "The parties hereby agree to the following terms and conditions.",
          description: undefined,
        }),
        // TanStack Query v5 passes (variables, context) to mutationFn.
        // The context is infrastructure, not part of the app contract.
        expect.anything(),
      ),
    );
    expect(await screen.findByText(/status page/i)).toBeInTheDocument();
  });

  it("shows a form-level error on server failure", async () => {
    const user = userEvent.setup();
    vi.mocked(analysisApi.submitAnalysis).mockRejectedValue(
      new HttpError(500, "Internal server error"),
    );

    renderTree();

    await user.type(screen.getByLabelText(/contract title/i), "Title");
    await user.type(
      screen.getByLabelText(/contract text/i),
      "This is a sufficiently long contract text.",
    );

    const submitButton = screen.getByRole("button", {
      name: /start analysis/i,
    });
    await waitFor(() => expect(submitButton).toBeEnabled());
    await user.click(submitButton);

    expect(
      await screen.findByText(/internal server error/i),
    ).toBeInTheDocument();
  });

  it("maps 422 errors to their form fields", async () => {
    const user = userEvent.setup();
    vi.mocked(analysisApi.submitAnalysis).mockRejectedValue(
      new HttpError(422, "Validation failed", [
        {
          loc: ["body", "title"],
          msg: "Title is too long",
          type: "value_error",
        },
      ]),
    );

    renderTree();

    await user.type(screen.getByLabelText(/contract title/i), "Some title");
    await user.type(
      screen.getByLabelText(/contract text/i),
      "This is a sufficiently long contract text.",
    );

    const submitButton = screen.getByRole("button", {
      name: /start analysis/i,
    });
    await waitFor(() => expect(submitButton).toBeEnabled());
    await user.click(submitButton);

    expect(await screen.findByText(/title is too long/i)).toBeInTheDocument();
  });
});
