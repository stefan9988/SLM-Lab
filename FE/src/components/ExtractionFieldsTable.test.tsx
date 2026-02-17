import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ExtractionFieldsTable from "./ExtractionFieldsTable";

const mockFetchSchemas = vi.fn();

vi.mock("../utils/api", () => ({
  fetchSchemas: (...args: unknown[]) => mockFetchSchemas(...args),
  createSchema: vi.fn(),
  updateSchemaApi: vi.fn(),
  deleteSchemaApi: vi.fn(),
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

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  mockFetchSchemas.mockResolvedValue(schemasFixture);
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
            "No schemas available. Create one in the Schemas tab.",
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
});
