import '@testing-library/jest-dom';
import { configure, waitFor } from '@testing-library/react';
import { TextDecoder, TextEncoder } from 'util';

// Configure React Testing Library
configure({
  testIdAttribute: 'data-testid',
  asyncUtilTimeout: 5000,
});

// Global test utilities
global.waitFor = waitFor;

// Mock ResizeObserver for components that use it
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock IntersectionObserver for components that use it
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock matchMedia for responsive components
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock getComputedStyle for style calculations
Object.defineProperty(window, 'getComputedStyle', {
  value: () => ({
    getPropertyValue: () => '',
    zIndex: '0',
  }),
});

// Mock scrollTo for virtual scrolling components
Object.defineProperty(window, 'scrollTo', {
  value: jest.fn(),
});

// Mock localStorage for state management tests
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
});

// Mock URL.createObjectURL for file handling
Object.defineProperty(URL, 'createObjectURL', {
  value: jest.fn(() => 'mocked-url'),
});
Object.defineProperty(URL, 'revokeObjectURL', {
  value: jest.fn(),
});

// Mock File and Blob APIs for file upload tests
global.File = class File {
  constructor(chunks, filename, options = {}) {
    this.chunks = chunks;
    this.name = filename;
    this.size = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
    this.type = options.type || '';
    this.lastModified = options.lastModified || Date.now();
  }
};

global.Blob = class Blob {
  constructor(chunks, options = {}) {
    this.chunks = chunks;
    this.size = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
    this.type = options.type || '';
  }
};

// Add TextEncoder/TextEncoder for Node.js environment compatibility
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder as any;

// Mock Tauri API for desktop integration tests
const mockTauri = {
  invoke: jest.fn(),
  listen: jest.fn(),
  emit: jest.fn(),
};

// Mock @tauri-apps/api modules
jest.mock('@tauri-apps/api/core', () => ({
  invoke: mockTauri.invoke,
  listen: mockTauri.listen,
  emit: mockTauri.emit,
}));

jest.mock('@tauri-apps/api/window', () => ({
  getCurrent: () => ({
    label: 'main',
    title: 'AI Disk Cleaner',
    minimize: jest.fn(),
    maximize: jest.fn(),
    close: jest.fn(),
    setFocus: jest.fn(),
  }),
}));

jest.mock('@tauri-apps/api/dialog', () => ({
  open: jest.fn(),
  save: jest.fn(),
  ask: jest.fn(),
  confirm: jest.fn(),
  message: jest.fn(),
}));

jest.mock('@tauri-apps/api/fs', () => ({
  readTextFile: jest.fn(),
  writeFile: jest.fn(),
  exists: jest.fn(),
  createDir: jest.fn(),
  removeDir: jest.fn(),
}));

// Mock WebSocket for real-time communication tests
global.WebSocket = class WebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  constructor(url: string) {
    this.url = url;
    setTimeout(() => {
      this.onopen?.(new Event('open'));
    }, 0);
  }

  send() {}
  close() {}
  addEventListener() {}
  removeEventListener() {}

  url: string;
  readyState = WebSocket.OPEN;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
};

// Mock fetch for API tests
global.fetch = jest.fn() as jest.Mock;

// Mock AbortController for request cancellation
global.AbortController = class AbortController {
  signal = {
    aborted: false,
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  };
  abort() {
    this.signal.aborted = true;
  }
};

// Mock performance APIs
Object.defineProperty(window, 'performance', {
  value: {
    now: jest.fn(() => Date.now()),
    mark: jest.fn(),
    measure: jest.fn(),
    getEntriesByName: jest.fn(() => []),
    getEntriesByType: jest.fn(() => []),
  },
});

// Mock requestAnimationFrame for animations
global.requestAnimationFrame = jest.fn(cb => setTimeout(cb, 16));
global.cancelAnimationFrame = jest.fn(id => clearTimeout(id));

// Console filtering in tests (reduce noise)
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render is deprecated')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };

  console.warn = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('componentWillReceiveProps has been renamed')
    ) {
      return;
    }
    originalWarn.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
});

// Cleanup after each test
afterEach(() => {
  jest.clearAllMocks();
  localStorageMock.clear();
  sessionStorageMock.clear();
});

// Export global test utilities
export const createMockFile = (name: string, content: string, type = 'text/plain') => {
  const blob = new Blob([content], { type });
  return new File([blob], name, { type });
};

export const createMockFileList = (files: File[]) => {
  const fileList = {
    length: files.length,
    item: (index: number) => files[index] || null,
    [Symbol.iterator]: function* () {
      for (const file of files) {
        yield file;
      }
    },
    ...files,
  };
  return fileList as FileList;
};

export const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const mockApiResponse = <T>(data: T, delay = 0) => {
  return new Promise<T>(resolve => {
    setTimeout(() => resolve(data), delay);
  });
};

// Type declarations for test environment
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeValidTauriCommand(): R;
      toHaveProperThemeVariables(): R;
      toBeAccessibleComponent(): R;
    }
  }
}

// Custom matchers
expect.extend({
  toBeValidTauriCommand(received) {
    const pass = typeof received === 'string' && received.length > 0;
    return {
      message: () =>
        pass
          ? `expected ${received} not to be a valid Tauri command`
          : `expected ${received} to be a valid Tauri command`,
      pass,
    };
  },

  toHaveProperThemeVariables(received: string) {
    const hasBackground = received.includes('--background');
    const hasForeground = received.includes('--foreground');
    const hasPrimary = received.includes('--primary');
    const pass = hasBackground && hasForeground && hasPrimary;

    return {
      message: () =>
        pass
          ? `expected CSS not to have proper theme variables`
          : `expected CSS to have proper theme variables (--background, --foreground, --primary)`,
      pass,
    };
  },

  toBeAccessibleComponent(received: HTMLElement) {
    const hasLabel = received.hasAttribute('aria-label') || received.hasAttribute('aria-labelledby');
    const hasRole = received.hasAttribute('role');
    const pass = hasLabel || hasRole;

    return {
      message: () =>
        pass
          ? `expected element not to have accessibility attributes`
          : `expected element to have accessibility attributes (aria-label, aria-labelledby, or role)`,
      pass,
    };
  },
});