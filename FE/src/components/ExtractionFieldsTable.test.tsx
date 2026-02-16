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
    expect(screen.getAllByPlaceholderText("Page / section")).toHaveLength(2);
  });

  it("renders the Analyze Document button", async () => {
    render(<ExtractionFieldsTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText("Analyze Document")).toBeInTheDocument();
    });
  });

  it("enables Analyze Document button when schema is auto-selected", async () => {
    render(<ExtractionFieldsTable {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText("Analyze Document")).toBeEnabled();
    });
  });

  it("enables Analyze Document button when a schema is selected", async () => {
    const user = userEvent.setup();
    render(<ExtractionFieldsTable {...defaultProps} />);

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

      expect(screen.getByText("vendor")).toBeInTheDocument();
      expect(screen.getByText("amount")).toBeInTheDocument();
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

      expect(screen.getByText("vendor")).toBeInTheDocument();
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
});
