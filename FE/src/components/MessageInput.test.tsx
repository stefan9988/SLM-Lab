import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MessageInput from './MessageInput';

const defaultProps = {
  onSend: vi.fn(),
  disabled: false,
  streaming: false,
  onStop: vi.fn(),
};

function createFile(name: string, size: number, type = 'text/plain'): File {
  const content = new Uint8Array(size);
  return new File([content], name, { type });
}

function mockDataTransfer(files: File[]) {
  return { files, items: files.map((f) => ({ kind: 'file', getAsFile: () => f })) };
}

describe('MessageInput', () => {
  describe('drag and drop', () => {
    it('shows drop overlay on dragOver and hides on drop', () => {
      const { container } = render(<MessageInput {...defaultProps} />);
      const dropZone = container.firstElementChild!;

      fireEvent.dragOver(dropZone);
      expect(screen.getByText('Drop files here')).toBeInTheDocument();

      const file = createFile('test.txt', 100);
      fireEvent.drop(dropZone, { dataTransfer: mockDataTransfer([file]) });
      expect(screen.queryByText('Drop files here')).not.toBeInTheDocument();
    });

    it('adds file on drop', () => {
      const { container } = render(<MessageInput {...defaultProps} />);
      const dropZone = container.firstElementChild!;
      const file = createFile('readme.md', 500);

      fireEvent.drop(dropZone, { dataTransfer: mockDataTransfer([file]) });
      expect(screen.getByText('readme.md')).toBeInTheDocument();
    });

    it('hides overlay on dragLeave from container', () => {
      const { container } = render(<MessageInput {...defaultProps} />);
      const dropZone = container.firstElementChild!;

      fireEvent.dragEnter(dropZone);
      expect(screen.getByText('Drop files here')).toBeInTheDocument();

      fireEvent.dragLeave(dropZone, { relatedTarget: document.body });
      expect(screen.queryByText('Drop files here')).not.toBeInTheDocument();
    });

    it('shows error for file exceeding 10MB', () => {
      const { container } = render(<MessageInput {...defaultProps} />);
      const dropZone = container.firstElementChild!;
      const bigFile = createFile('huge.txt', 11 * 1024 * 1024);

      fireEvent.drop(dropZone, { dataTransfer: mockDataTransfer([bigFile]) });
      expect(screen.getByText(/exceeds 10MB limit/)).toBeInTheDocument();
      expect(screen.queryByText('huge.txt')).not.toBeInTheDocument();
    });

    it('shows error when total size exceeds 20MB', () => {
      const { container } = render(<MessageInput {...defaultProps} />);
      const dropZone = container.firstElementChild!;

      // Drop three files individually, each under 10MB but totalling > 20MB
      const file1 = createFile('a.txt', 8 * 1024 * 1024);
      fireEvent.drop(dropZone, { dataTransfer: mockDataTransfer([file1]) });
      expect(screen.getByText('a.txt')).toBeInTheDocument();

      const file2 = createFile('b.txt', 8 * 1024 * 1024);
      fireEvent.drop(dropZone, { dataTransfer: mockDataTransfer([file2]) });
      expect(screen.getByText('b.txt')).toBeInTheDocument();

      const file3 = createFile('c.txt', 8 * 1024 * 1024);
      fireEvent.drop(dropZone, { dataTransfer: mockDataTransfer([file3]) });
      expect(screen.getByText(/Total file size exceeds 20MB limit/)).toBeInTheDocument();
    });
  });

  describe('clipboard paste', () => {
    it('adds pasted image file', () => {
      render(<MessageInput {...defaultProps} />);
      const textarea = screen.getByPlaceholderText('Type a message…');
      const imageFile = createFile('image.png', 200, 'image/png');

      const pasteEvent = new Event('paste', { bubbles: true }) as any;
      pasteEvent.clipboardData = {
        items: [{ kind: 'file', getAsFile: () => imageFile }],
      };

      fireEvent(textarea, pasteEvent);
      expect(screen.getByText('image.png')).toBeInTheDocument();
    });

    it('does not interfere with text paste', async () => {
      const user = userEvent.setup();
      render(<MessageInput {...defaultProps} />);
      const textarea = screen.getByPlaceholderText('Type a message…');

      await user.click(textarea);
      await user.paste('hello world');

      expect(textarea).toHaveValue('hello world');
      // No file tags should appear
      expect(screen.queryByText('×')).not.toBeInTheDocument();
    });
  });

  describe('click-to-attach still works', () => {
    it('adds files via the hidden file input', () => {
      render(<MessageInput {...defaultProps} />);
      const fileInput = document.querySelector('input[type="file"]')!;
      const file = createFile('doc.pdf', 300, 'application/pdf');

      fireEvent.change(fileInput, { target: { files: [file] } });
      expect(screen.getByText('doc.pdf')).toBeInTheDocument();
    });
  });
});
