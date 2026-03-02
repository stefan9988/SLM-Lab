import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ExtractionFieldsTable from "./ExtractionFieldsTable";

const mockFetchSchemas = vi.fn();
const mockStreamAnalyzeDocument = vi.fn();
const mockStreamValidate = vi.fn();
const mockFetchValidationResults = vi.fn();

vi.mock("../utils/api", () => ({
  fetchSchemas: (...args: unknown[]) => mockFetchSchemas(...args),
  createSchema: vi.fn(),
  updateSchemaApi: vi.fn(),
  deleteSchemaApi: vi.fn(),
  streamAnalyzeDocument: (...args: unknown[]) => mockStreamAnalyzeDocument(...args),
  streamValidate: (...args: unknown[]) => mockStreamValidate(...args),
  fetchValidationResults: (...args: unknown[]) => mockFetchValidationResults(...args),
}));

const TEST_SESSION_ID = "test-uuid-1234-5678-abcd-ef0123456789";

vi.mock("uuid", () => ({
  v4: () => TEST_SESSION_ID,
}));

const defaultProps = {
  onLoadDocument: vi.fn(),
};

const schemasFixture = [
  {
    id: "s1",
    name: "Invoice Schema",
    fields: [
      { id: "f1", key: "vendor", description: "Vendor name" },
      { id: "f2", key: "amount", description: "Total amount" },
    ],
  },
  {
    id: "s2",
    name: "Empty Schema",
    fields: [],
  },
];

async function* makeAnalyzeGen(
  events: Array<{ type: string; content: unknown }>,
) {
  for (const e of events) {
    yield e;
  }
  yield "DONE" as const;
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  mockFetchSchemas.mockResolvedValue(schemasFixture);
  mockFetchValidationResults.mockResolvedValue(null);
});

describe("ExtractionFieldsTable", () => {
  it("renders schema dropdown", async () => {
    render(<ExtractionFieldsTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByLabelText("Extraction Schema")).toBeInTheDocument();
    });
  });

  it("populates dropdown with fetched schemas", async () => {
    render(<ExtractionFieldsTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText("Invoice Schema")).toBeInTheDocument();
      expect(screen.getByText("Empty Schema")).toBeInTheDocument();
    });
  });

  it("shows field rows when a schema is selected", async () => {
    const user = userEvent.setup();
    render(<ExtractionFieldsTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText("Invoice Schema")).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText("Extraction Schema"), "s1");

    expect(screen.getByText("vendor")).toBeInTheDocument();
    expect(screen.getByText("amount")).toBeInTheDocument();
    expect(screen.getAllByPlaceholderText("Extracted value")).toHaveLength(2);
  });

  it("renders the Analyze Document button", async () => {
    render(<ExtractionFieldsTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText("Analyze Document")).toBeInTheDocument();
    });
  });

  it("enables Analyze Document button when schema is auto-selected", async () => {
    const file = new File(["x"], "test.pdf", { type: "application/pdf" });
    render(<ExtractionFieldsTable {...defaultProps} file={file} />);

    await waitFor(() => {
      expect(screen.getByText("Analyze Document")).toBeEnabled();
    });
  });

  it("enables Analyze Document button when a schema is selected", async () => {
    const user = userEvent.setup();
    const file = new File(["x"], "test.pdf", { type: "application/pdf" });
    render(<ExtractionFieldsTable {...defaultProps} file={file} />);

    await waitFor(() => {
      expect(screen.getByText("Invoice Schema")).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText("Extraction Schema"), "s1");

    expect(screen.getByText("Analyze Document")).toBeEnabled();
  });

  it('renders "Choose File" button when no document is loaded', async () => {
    render(<ExtractionFieldsTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText("Choose File")).toBeInTheDocument();
    });
  });

  it("shows document name when provided", async () => {
    render(
      <ExtractionFieldsTable {...defaultProps} documentName="report.pdf" />,
    );

    await waitFor(() => {
      expect(screen.getByText("report.pdf")).toBeInTheDocument();
    });
  });

  it("calls onLoadDocument when a file is selected", async () => {
    const onLoadDocument = vi.fn();
    render(<ExtractionFieldsTable onLoadDocument={onLoadDocument} />);

    const file = new File(["dummy"], "test.pdf", { type: "application/pdf" });
    const input = screen.getByTestId("file-input") as HTMLInputElement;

    await userEvent.upload(input, file);

    expect(onLoadDocument).toHaveBeenCalledWith(file);
  });

  describe("auto-select schema", () => {
    it("auto-selects first schema when no last-used schema in localStorage", async () => {
      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        const select = screen.getByLabelText(
          "Extraction Schema",
        ) as HTMLSelectElement;
        expect(select.value).toBe("s1");
      });

      await waitFor(() => {
        expect(screen.getByText("vendor")).toBeInTheDocument();
        expect(screen.getByText("amount")).toBeInTheDocument();
      });
    });

    it("auto-selects last-used schema from localStorage when it matches", async () => {
      localStorage.setItem("slm-last-schema-id", "s2");

      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        const select = screen.getByLabelText(
          "Extraction Schema",
        ) as HTMLSelectElement;
        expect(select.value).toBe("s2");
      });
    });

    it("falls back to first schema when localStorage schema ID does not match any", async () => {
      localStorage.setItem("slm-last-schema-id", "nonexistent");

      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        const select = screen.getByLabelText(
          "Extraction Schema",
        ) as HTMLSelectElement;
        expect(select.value).toBe("s1");
      });

      await waitFor(() => {
        expect(screen.getByText("vendor")).toBeInTheDocument();
      });
    });

    it("persists selected schema ID to localStorage on change", async () => {
      const user = userEvent.setup();
      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText("Empty Schema")).toBeInTheDocument();
      });

      await user.selectOptions(
        screen.getByLabelText("Extraction Schema"),
        "s2",
      );

      expect(localStorage.getItem("slm-last-schema-id")).toBe("s2");
    });
  });

  describe("Clear button", () => {
    it("is visible when rows exist", async () => {
      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText("vendor")).toBeInTheDocument();
      });

      expect(screen.getByText("Clear")).toBeInTheDocument();
    });

    it("is not visible when schema has no fields", async () => {
      const user = userEvent.setup();
      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText("Empty Schema")).toBeInTheDocument();
      });

      await user.selectOptions(
        screen.getByLabelText("Extraction Schema"),
        "s2",
      );

      expect(screen.queryByText("Clear")).not.toBeInTheDocument();
    });

    it("clears extraction values and status text when clicked", async () => {
      const user = userEvent.setup();
      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText("vendor")).toBeInTheDocument();
      });

      const inputs = screen.getAllByPlaceholderText("Extracted value");
      await user.type(inputs[0], "Acme Corp");
      expect(inputs[0]).toHaveValue("Acme Corp");

      await user.click(screen.getByText("Clear"));

      const updatedInputs = screen.getAllByPlaceholderText("Extracted value");
      updatedInputs.forEach((input) => {
        expect(input).toHaveValue("");
      });
    });

    it("calls onHighlightClear when Clear is clicked", async () => {
      const user = userEvent.setup();
      const onHighlightClear = vi.fn();
      render(
        <ExtractionFieldsTable
          {...defaultProps}
          onHighlightClear={onHighlightClear}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("vendor")).toBeInTheDocument();
      });

      await user.click(screen.getByText("Clear"));

      expect(onHighlightClear).toHaveBeenCalled();
    });
  });

  describe("Save as CSV button", () => {
    it("is visible when rows exist", async () => {
      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText("vendor")).toBeInTheDocument();
      });

      expect(screen.getByText("Save as CSV")).toBeInTheDocument();
    });

    it("is disabled when all extractions are empty", async () => {
      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText("vendor")).toBeInTheDocument();
      });

      expect(screen.getByText("Save as CSV")).toBeDisabled();
    });

    it("is enabled when at least one extraction has a value", async () => {
      const user = userEvent.setup();
      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText("vendor")).toBeInTheDocument();
      });

      const inputs = screen.getAllByPlaceholderText("Extracted value");
      await user.type(inputs[0], "Acme Corp");

      expect(screen.getByText("Save as CSV")).toBeEnabled();
    });

    it("includes edited extraction values in the CSV content", async () => {
      const user = userEvent.setup();
      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText("vendor")).toBeInTheDocument();
      });

      const inputs = screen.getAllByPlaceholderText("Extracted value");
      await user.type(inputs[0], 'Acme "Corp"');
      await user.type(inputs[1], "1234.56");

      let capturedBlob: Blob | null = null;
      vi.spyOn(URL, "createObjectURL").mockImplementation((blob: Blob) => {
        capturedBlob = blob;
        return "blob:fake";
      });
      vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

      const origCreateElement = document.createElement.bind(document);
      vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
        if (tag === "a") {
          return {
            set href(_v: string) {},
            download: "",
            click: vi.fn(),
          } as unknown as HTMLAnchorElement;
        }
        return origCreateElement(tag);
      });

      await user.click(screen.getByText("Save as CSV"));

      expect(capturedBlob).not.toBeNull();
      const reader = new FileReader();
      const text = await new Promise<string>((resolve) => {
        reader.onload = () => resolve(reader.result as string);
        reader.readAsText(capturedBlob!);
      });
      const lines = text.split("\n");
      expect(lines[0]).toBe("key,extraction,location");
      expect(lines[1]).toBe('"vendor","Acme ""Corp""","-"');
      expect(lines[2]).toBe('"amount","1234.56","-"');

      vi.restoreAllMocks();
    });

    it("becomes disabled again after Clear is clicked", async () => {
      const user = userEvent.setup();
      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText("vendor")).toBeInTheDocument();
      });

      const inputs = screen.getAllByPlaceholderText("Extracted value");
      await user.type(inputs[0], "Acme Corp");
      expect(screen.getByText("Save as CSV")).toBeEnabled();

      await user.click(screen.getByText("Clear"));

      expect(screen.getByText("Save as CSV")).toBeDisabled();
    });
  });

  describe("clickable location cells", () => {
    it("renders location as plain text when location is null", async () => {
      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText("vendor")).toBeInTheDocument();
      });

      // With no extraction data, locations should be plain text dashes
      const locationCells = screen.getAllByText("-");
      expect(locationCells.length).toBeGreaterThan(0);
      locationCells.forEach((cell) => {
        expect(cell.tagName).not.toBe("BUTTON");
      });
    });

    it("renders location as plain text when extraction is empty", async () => {
      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText("vendor")).toBeInTheDocument();
      });

      // Locations without extraction should not be buttons
      const dashes = screen.getAllByText("-");
      dashes.forEach((el) => {
        expect(el.tagName).not.toBe("BUTTON");
      });
    });
  });

  describe("empty schemas", () => {
    it('shows "no schemas" message when schema list is empty', async () => {
      mockFetchSchemas.mockResolvedValue([]);

      render(<ExtractionFieldsTable {...defaultProps} />);

      await waitFor(() => {
        expect(
          screen.getByText(
            "No schemas yet — create one in the Schemas tab to get started.",
          ),
        ).toBeInTheDocument();
      });

      expect(
        screen.queryByLabelText("Extraction Schema"),
      ).not.toBeInTheDocument();
    });
  });

  describe("onHighlightClear on schema change", () => {
    it("calls onHighlightClear when schema is changed", async () => {
      const user = userEvent.setup();
      const onHighlightClear = vi.fn();
      render(
        <ExtractionFieldsTable
          {...defaultProps}
          onHighlightClear={onHighlightClear}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Empty Schema")).toBeInTheDocument();
      });

      await user.selectOptions(
        screen.getByLabelText("Extraction Schema"),
        "s2",
      );

      expect(onHighlightClear).toHaveBeenCalled();
    });
  });

  describe("Continue chatting button", () => {
    const file = new File(["x"], "test.pdf", { type: "application/pdf" });

    it("is not shown before analysis runs", async () => {
      render(<ExtractionFieldsTable {...defaultProps} file={file} />);

      await waitFor(() => {
        expect(screen.getByText("Analyze Document")).toBeInTheDocument();
      });

      expect(
        screen.queryByText("Continue chatting about this document"),
      ).not.toBeInTheDocument();
    });

    it("appears after successful analysis", async () => {
      const user = userEvent.setup();
      mockStreamAnalyzeDocument.mockImplementation(() =>
        makeAnalyzeGen([
          { type: "extraction", content: { key: "vendor", extraction: "Acme", location: null } },
        ]),
      );

      render(
        <ExtractionFieldsTable
          {...defaultProps}
          file={file}
          onContinueChat={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Analyze Document")).toBeEnabled();
      });

      await act(async () => {
        await user.click(screen.getByText("Analyze Document"));
      });

      await waitFor(() => {
        expect(
          screen.getByText("Continue chatting about this document"),
        ).toBeInTheDocument();
      });
    });

    it("is hidden while analyzing", async () => {
      const user = userEvent.setup();
      // Never resolves during the test
      let resolve!: () => void;
      const pending = new Promise<void>((r) => { resolve = r; });
      mockStreamAnalyzeDocument.mockImplementation(async function* () {
        await pending;
        yield "DONE" as const;
      });

      render(<ExtractionFieldsTable {...defaultProps} file={file} />);

      await waitFor(() => {
        expect(screen.getByText("Analyze Document")).toBeEnabled();
      });

      await user.click(screen.getByText("Analyze Document"));

      expect(
        screen.queryByText("Continue chatting about this document"),
      ).not.toBeInTheDocument();

      resolve();
    });

    it("is not shown after analysis with a fatal error", async () => {
      const user = userEvent.setup();
      mockStreamAnalyzeDocument.mockImplementation(async function* () {
        throw new Error("Network failure");
        yield "DONE" as const; // eslint-disable-line no-unreachable
      });

      render(<ExtractionFieldsTable {...defaultProps} file={file} />);

      await waitFor(() => {
        expect(screen.getByText("Analyze Document")).toBeEnabled();
      });

      await act(async () => {
        await user.click(screen.getByText("Analyze Document"));
      });

      await waitFor(() => {
        expect(screen.getByText(/Something went wrong/)).toBeInTheDocument();
      });

      expect(
        screen.queryByText("Continue chatting about this document"),
      ).not.toBeInTheDocument();
    });

    it("disappears when Clear is clicked", async () => {
      const user = userEvent.setup();
      mockStreamAnalyzeDocument.mockImplementation(() => makeAnalyzeGen([]));

      render(
        <ExtractionFieldsTable
          {...defaultProps}
          file={file}
          onContinueChat={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Analyze Document")).toBeEnabled();
      });

      await act(async () => {
        await user.click(screen.getByText("Analyze Document"));
      });

      await waitFor(() => {
        expect(
          screen.getByText("Continue chatting about this document"),
        ).toBeInTheDocument();
      });

      await user.click(screen.getByText("Clear"));

      expect(
        screen.queryByText("Continue chatting about this document"),
      ).not.toBeInTheDocument();
    });

    it("calls onContinueChat with the session ID when clicked", async () => {
      const user = userEvent.setup();
      const onContinueChat = vi.fn();
      mockStreamAnalyzeDocument.mockImplementation(() => makeAnalyzeGen([]));

      render(
        <ExtractionFieldsTable
          {...defaultProps}
          file={file}
          onContinueChat={onContinueChat}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Analyze Document")).toBeEnabled();
      });

      await act(async () => {
        await user.click(screen.getByText("Analyze Document"));
      });

      await waitFor(() => {
        expect(
          screen.getByText("Continue chatting about this document"),
        ).toBeInTheDocument();
      });

      await user.click(screen.getByText("Continue chatting about this document"));

      expect(onContinueChat).toHaveBeenCalledWith(TEST_SESSION_ID, 'document');
    });

    it("passes the document name to onContinueChat", async () => {
      const user = userEvent.setup();
      const onContinueChat = vi.fn();
      mockStreamAnalyzeDocument.mockImplementation(() => makeAnalyzeGen([]));

      render(
        <ExtractionFieldsTable
          {...defaultProps}
          file={file}
          documentName="report.pdf"
          onContinueChat={onContinueChat}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Analyze Document")).toBeEnabled();
      });

      await act(async () => {
        await user.click(screen.getByText("Analyze Document"));
      });

      await waitFor(() => {
        expect(
          screen.getByText("Continue chatting about this document"),
        ).toBeInTheDocument();
      });

      await user.click(screen.getByText("Continue chatting about this document"));

      expect(onContinueChat).toHaveBeenCalledWith(TEST_SESSION_ID, 'report.pdf');
    });
  });

  describe("Validation UI", () => {
    const file = new File(["x"], "test.pdf", { type: "application/pdf" });

    async function runAnalysis(user: ReturnType<typeof userEvent.setup>) {
      mockStreamAnalyzeDocument.mockImplementation(() =>
        makeAnalyzeGen([
          {
            type: "extraction",
            content: { key: "vendor", extraction: "Acme Corp", location: null },
          },
          {
            type: "extraction",
            content: { key: "amount", extraction: "1000", location: null },
          },
        ]),
      );

      render(
        <ExtractionFieldsTable
          {...defaultProps}
          file={file}
          onContinueChat={vi.fn()}
        />,
      );

      await waitFor(() => {
        expect(screen.getByText("Analyze Document")).toBeEnabled();
      });

      await act(async () => {
        await user.click(screen.getByText("Analyze Document"));
      });

      await waitFor(() => {
        expect(
          screen.getByText("Continue chatting about this document"),
        ).toBeInTheDocument();
      });

      // Open the validation panel
      await user.click(screen.getByTestId("validate-toggle-button"));
      await waitFor(() => {
        expect(screen.getByTestId("validation-url-input-0")).toBeInTheDocument();
      });
    }

    async function* makeValidateGen(
      events: Array<{ type: string; content: unknown }>,
    ) {
      for (const e of events) {
        yield e;
      }
      yield "DONE" as const;
    }

    it("validation UI is not shown before analysis completes", async () => {
      render(<ExtractionFieldsTable {...defaultProps} file={file} />);

      await waitFor(() => {
        expect(screen.getByText("Analyze Document")).toBeInTheDocument();
      });

      expect(screen.queryByTestId("validate-toggle-button")).not.toBeInTheDocument();
      expect(screen.queryByTestId("validate-button")).not.toBeInTheDocument();
    });

    it("validation section appears after analysis completes", async () => {
      const user = userEvent.setup();
      mockStreamAnalyzeDocument.mockImplementation(() =>
        makeAnalyzeGen([
          { type: "extraction", content: { key: "vendor", extraction: "Acme Corp", location: null } },
          { type: "extraction", content: { key: "amount", extraction: "1000", location: null } },
        ]),
      );

      render(
        <ExtractionFieldsTable {...defaultProps} file={file} onContinueChat={vi.fn()} />,
      );

      await waitFor(() => {
        expect(screen.getByText("Analyze Document")).toBeEnabled();
      });

      await act(async () => {
        await user.click(screen.getByText("Analyze Document"));
      });

      await waitFor(() => {
        expect(screen.getByTestId("validate-toggle-button")).toBeInTheDocument();
      });

      // "Analyze Document" is replaced by the Validate toggle
      expect(screen.queryByText("Analyze Document")).not.toBeInTheDocument();
      // Panel is closed — Run Validation button not yet visible
      expect(screen.queryByTestId("validate-button")).not.toBeInTheDocument();

      // Click toggle to open panel
      await user.click(screen.getByTestId("validate-toggle-button"));
      await waitFor(() => {
        expect(screen.getByTestId("validate-button")).toBeInTheDocument();
      });
    });

    it("can add a second URL input", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      const addBtn = screen.getByTestId("add-url-button");
      await user.click(addBtn);

      expect(screen.getAllByTestId(/validation-url-input-/)).toHaveLength(2);
    });

    it("remove button only appears when there is more than one URL input", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      // Only one input — no remove button
      expect(screen.queryByLabelText("Remove URL")).not.toBeInTheDocument();

      // Add a second URL
      await user.click(screen.getByTestId("add-url-button"));

      // Now remove buttons should appear
      const removeBtns = screen.getAllByLabelText("Remove URL");
      expect(removeBtns).toHaveLength(2);
    });

    it("removing a URL input decreases the count", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      await user.click(screen.getByTestId("add-url-button"));
      expect(screen.getAllByTestId(/validation-url-input-/)).toHaveLength(2);

      const removeBtns = screen.getAllByLabelText("Remove URL");
      await user.click(removeBtns[0]);

      expect(screen.getAllByTestId(/validation-url-input-/)).toHaveLength(1);
    });

    it("validate button is disabled when URL input is empty", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      // Input is empty by default
      expect(screen.getByTestId("validate-button")).toBeDisabled();
    });

    it("validate button is enabled when URL is filled in", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      const urlInput = screen.getByTestId("validation-url-input-0");
      await user.type(urlInput, "https://acme.example.com");

      expect(screen.getByTestId("validate-button")).toBeEnabled();
    });

    it("renders status dots after validation_complete event", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      mockStreamValidate.mockImplementation(() =>
        makeValidateGen([
          {
            type: "validation_complete",
            content: [
              {
                claim: "vendor: Acme Corp",
                status: "correct",
                validated_value: "Acme Corporation",
                sources: ["https://acme.example.com/about"],
              },
              {
                claim: "amount: 1000",
                status: "incorrect",
                validated_value: "2000",
                sources: ["https://acme.example.com/invoice"],
              },
            ],
          },
        ]),
      );

      const urlInput = screen.getByTestId("validation-url-input-0");
      await user.type(urlInput, "https://acme.example.com");

      await act(async () => {
        await user.click(screen.getByTestId("validate-button"));
      });

      await waitFor(() => {
        // green dot for vendor (correct), red dot for amount (incorrect)
        const greenDots = document.querySelectorAll(".bg-green-400");
        const redDots = document.querySelectorAll(".bg-red-400");
        expect(greenDots.length).toBeGreaterThanOrEqual(1);
        expect(redDots.length).toBeGreaterThanOrEqual(1);
      });
    });

    it("source column appears only after validation", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      // No validated column before validation
      expect(screen.queryByText("Validated")).not.toBeInTheDocument();

      mockStreamValidate.mockImplementation(() =>
        makeValidateGen([
          {
            type: "validation_complete",
            content: [
              {
                claim: "vendor: Acme Corp",
                status: "correct",
                validated_value: "Acme Corporation",
                sources: ["https://acme.example.com/about"],
              },
            ],
          },
        ]),
      );

      const urlInput = screen.getByTestId("validation-url-input-0");
      await user.type(urlInput, "https://acme.example.com");

      await act(async () => {
        await user.click(screen.getByTestId("validate-button"));
      });

      await waitFor(() => {
        expect(screen.getByText("Validated")).toBeInTheDocument();
      });
    });

    it("clear button resets validation state", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      mockStreamValidate.mockImplementation(() =>
        makeValidateGen([
          {
            type: "validation_complete",
            content: [
              {
                claim: "vendor: Acme Corp",
                status: "correct",
                validated_value: "Acme Corporation",
                sources: ["https://acme.example.com"],
              },
            ],
          },
        ]),
      );

      const urlInput = screen.getByTestId("validation-url-input-0");
      await user.type(urlInput, "https://acme.example.com");

      await act(async () => {
        await user.click(screen.getByTestId("validate-button"));
      });

      await waitFor(() => {
        expect(screen.getByText("Validated")).toBeInTheDocument();
      });

      await user.click(screen.getByText("Clear"));

      expect(screen.queryByText("Validated")).not.toBeInTheDocument();
      expect(screen.queryByTestId("validate-toggle-button")).not.toBeInTheDocument();
    });

    it("hides Load Document and Extraction Schema after analysis completes", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      expect(screen.queryByText("Load Document")).not.toBeInTheDocument();
      expect(screen.queryByLabelText("Extraction Schema")).not.toBeInTheDocument();
    });

    it("shows Load Document and Extraction Schema again after Clear", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      await user.click(screen.getByText("Clear"));

      await waitFor(() => {
        expect(screen.getByText("Load Document")).toBeInTheDocument();
        expect(screen.getByLabelText("Extraction Schema")).toBeInTheDocument();
      });
    });

    it("hides Validate toggle after validation completes", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      mockStreamValidate.mockImplementation(() =>
        makeValidateGen([
          {
            type: "validation_complete",
            content: [
              {
                claim: "vendor: Acme Corp",
                status: "correct",
                validated_value: "Acme Corporation",
                sources: ["https://acme.example.com/about"],
              },
            ],
          },
        ]),
      );

      const urlInput = screen.getByTestId("validation-url-input-0");
      await user.type(urlInput, "https://acme.example.com");

      await act(async () => {
        await user.click(screen.getByTestId("validate-button"));
      });

      await waitFor(() => {
        expect(screen.queryByTestId("validate-toggle-button")).not.toBeInTheDocument();
      });
    });

    it("shows validated_value in Validated column", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      mockStreamValidate.mockImplementation(() =>
        makeValidateGen([
          {
            type: "validation_complete",
            content: [
              {
                claim: "vendor: Acme Corp",
                status: "correct",
                validated_value: "Acme Corporation",
                sources: ["https://acme.example.com/about"],
              },
            ],
          },
        ]),
      );

      const urlInput = screen.getByTestId("validation-url-input-0");
      await user.type(urlInput, "https://acme.example.com");

      await act(async () => {
        await user.click(screen.getByTestId("validate-button"));
      });

      await waitFor(() => {
        expect(screen.getByText("Acme Corporation")).toBeInTheDocument();
      });
    });

    it("shows citation links with source URL tooltips", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      mockStreamValidate.mockImplementation(() =>
        makeValidateGen([
          {
            type: "validation_complete",
            content: [
              {
                claim: "vendor: Acme Corp",
                status: "correct",
                validated_value: "Acme Corporation",
                sources: ["https://acme.example.com/about"],
              },
            ],
          },
        ]),
      );

      const urlInput = screen.getByTestId("validation-url-input-0");
      await user.type(urlInput, "https://acme.example.com");

      await act(async () => {
        await user.click(screen.getByTestId("validate-button"));
      });

      await waitFor(() => {
        const citationLink = screen.getByText("[1]");
        expect(citationLink).toBeInTheDocument();
        expect(citationLink).toHaveAttribute("title", "https://acme.example.com/about");
        expect(citationLink).toHaveAttribute("href", "https://acme.example.com/about");
      });
    });

    it("status dot title shows status label not validated value", async () => {
      const user = userEvent.setup();
      await runAnalysis(user);

      mockStreamValidate.mockImplementation(() =>
        makeValidateGen([
          {
            type: "validation_complete",
            content: [
              {
                claim: "vendor: Acme Corp",
                status: "correct",
                validated_value: "Acme Corporation",
                sources: ["https://acme.example.com/about"],
              },
              {
                claim: "amount: 1000",
                status: "not_found",
                validated_value: null,
                sources: [],
              },
            ],
          },
        ]),
      );

      const urlInput = screen.getByTestId("validation-url-input-0");
      await user.type(urlInput, "https://acme.example.com");

      await act(async () => {
        await user.click(screen.getByTestId("validate-button"));
      });

      await waitFor(() => {
        const greenDot = document.querySelector(".bg-green-400");
        expect(greenDot).toHaveAttribute("title", "correct");
        const yellowDot = document.querySelector(".bg-yellow-400");
        expect(yellowDot).toHaveAttribute("title", "not found");
      });
    });
  });
});
