// Polyfills for Jest test environment
import { TextDecoder, TextEncoder } from 'util';

// TextEncoder/TextDecoder polyfill for Node.js environment
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Fetch polyfill for Node.js environment
import { fetch } from 'whatwg-fetch';
global.fetch = fetch;

// Web Crypto API polyfill
import { Crypto } from '@peculiar/webcrypto';
global.crypto = new Crypto();

// URL and URLSearchParams polyfills
import { URL, URLSearchParams } from 'whatwg-url';
global.URL = URL;
global.URLSearchParams = URLSearchParams;

// AbortController polyfill
import { AbortController } from 'abort-controller';
global.AbortController = AbortController;

// Blob polyfill
import { Blob } from 'cross-blob';
global.Blob = Blob;

// File polyfill
global.File = class File extends Blob {
  constructor(chunks, filename, options = {}) {
    super(chunks, options);
    this.name = filename;
    this.lastModified = options.lastModified || Date.now();
    this.size = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
    this.type = options.type || '';
  }
};

// FileReader polyfill
global.FileReader = class FileReader {
  constructor() {
    this.readyState = 0;
    this.result = null;
    this.error = null;
    this.onload = null;
    this.onerror = null;
    this.onloadend = null;
  }

  readAsText() {
    setTimeout(() => {
      this.readyState = 2;
      this.result = 'mock file content';
      this.onload?.({ target: this });
      this.onloadend?.({ target: this });
    }, 0);
  }

  readAsDataURL() {
    setTimeout(() => {
      this.readyState = 2;
      this.result = 'data:text/plain;base64,bW9jayBmaWxlIGNvbnRlbnQ=';
      this.onload?.({ target: this });
      this.onloadend?.({ target: this });
    }, 0);
  }
};

// FormData polyfill
global.FormData = class FormData {
  constructor() {
    this.data = new Map();
  }

  append(name, value) {
    this.data.set(name, value);
  }

  get(name) {
    return this.data.get(name);
  }

  has(name) {
    return this.data.has(name);
  }

  delete(name) {
    this.data.delete(name);
  }

  entries() {
    return this.data.entries();
  }

  keys() {
    return this.data.keys();
  }

  values() {
    return this.data.values();
  }
};

// Headers polyfill
global.Headers = class Headers {
  constructor(init = {}) {
    this.data = new Map();
    if (init) {
      Object.entries(init).forEach(([key, value]) => {
        this.data.set(key, value);
      });
    }
  }

  append(name, value) {
    this.data.set(name, value);
  }

  get(name) {
    return this.data.get(name);
  }

  has(name) {
    return this.data.has(name);
  }

  delete(name) {
    this.data.delete(name);
  }

  entries() {
    return this.data.entries();
  }

  keys() {
    return this.data.keys();
  }

  values() {
    return this.data.values();
  }
};

// Request and Response polyfills
global.Request = class Request {
  constructor(input, init = {}) {
    this.url = typeof input === 'string' ? input : input.url;
    this.method = init.method || 'GET';
    this.headers = new Headers(init.headers);
    this.body = init.body;
    this.mode = init.mode || 'cors';
    this.credentials = init.credentials || 'same-origin';
    this.cache = init.cache || 'default';
    this.redirect = init.redirect || 'follow';
    this.referrer = init.referrer || 'about:client';
    this.referrerPolicy = init.referrerPolicy || '';
    this.integrity = init.integrity || '';
    this.keepalive = init.keepalive || false;
    this.signal = init.signal || null;
  }
};

global.Response = class Response {
  constructor(body = null, init = {}) {
    this.body = body;
    this.status = init.status || 200;
    this.statusText = init.statusText || 'OK';
    this.headers = new Headers(init.headers);
    this.url = init.url || '';
    this.redirected = init.redirected || false;
    this.type = init.type || 'basic';
    this.ok = this.status >= 200 && this.status < 300;
  }

  async text() {
    return this.body || '';
  }

  async json() {
    return this.body ? JSON.parse(this.body) : {};
  }

  async blob() {
    return new Blob([this.body || '']);
  }

  async arrayBuffer() {
    return new TextEncoder().encode(this.body || '').buffer;
  }
};

// WebSocket polyfill for tests
global.WebSocket = class WebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  constructor(url) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;
    this.protocol = '';
    this.extensions = '';
    this.bufferedAmount = 0;
    this.binaryType = 'blob';

    // Simulate connection
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      this.onopen?.({ type: 'open' });
    }, 10);
  }

  send(data) {
    if (this.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Mock send
  }

  close(code, reason) {
    this.readyState = WebSocket.CLOSING;
    setTimeout(() => {
      this.readyState = WebSocket.CLOSED;
      this.onclose?.({ type: 'close', code: code || 1000, reason: reason || '' });
    }, 10);
  }

  addEventListener(type, listener) {
    this[`on${type}`] = listener;
  }

  removeEventListener(type, listener) {
    if (this[`on${type}`] === listener) {
      this[`on${type}`] = null;
    }
  }
};

// Event polyfill
global.Event = class Event {
  constructor(type, eventInitDict = {}) {
    this.type = type;
    this.bubbles = eventInitDict.bubbles || false;
    this.cancelable = eventInitDict.cancelable || false;
    this.timeStamp = Date.now();
    this.defaultPrevented = false;
  }

  preventDefault() {
    this.defaultPrevented = true;
  }

  stopPropagation() {}
};

global.CustomEvent = class CustomEvent extends Event {
  constructor(type, eventInitDict = {}) {
    super(type, eventInitDict);
    this.detail = eventInitDict.detail;
  }
};

global.MessageEvent = class MessageEvent extends Event {
  constructor(type, eventInitDict = {}) {
    super(type, eventInitDict);
    this.data = eventInitDict.data;
    this.origin = eventInitDict.origin || '';
    this.lastEventId = eventInitDict.lastEventId || '';
    this.source = eventInitDict.source || null;
    this.ports = eventInitDict.ports || [];
  }
};

global.CloseEvent = class CloseEvent extends Event {
  constructor(type, eventInitDict = {}) {
    super(type, eventInitDict);
    this.wasClean = eventInitDict.wasClean || false;
    this.code = eventInitDict.code || 0;
    this.reason = eventInitDict.reason || '';
  }
};

// Performance API polyfill
global.performance = {
  now: () => Date.now(),
  timing: {
    navigationStart: Date.now(),
    loadEventEnd: Date.now(),
  },
  mark: () => {},
  measure: () => {},
  getEntriesByName: () => [],
  getEntriesByType: () => [],
  getEntries: () => [],
  clearMarks: () => {},
  clearMeasures: () => {},
  clearResourceTimings: () => {},
};

// RequestAnimationFrame polyfill
global.requestAnimationFrame = callback => {
  return setTimeout(() => callback(Date.now()), 16);
};

global.cancelAnimationFrame = id => {
  clearTimeout(id);
};

// Console polyfill for better test output
const originalConsole = console;

console = {
  ...originalConsole,
  // Suppress certain warnings in tests
  warn: (message, ...args) => {
    if (
      typeof message === 'string' &&
      (message.includes('componentWillReceiveProps') ||
       message.includes('componentWillUpdate') ||
       message.includes('UNSAFE_'))
    ) {
      return;
    }
    originalConsole.warn(message, ...args);
  },
  error: (message, ...args) => {
    if (
      typeof message === 'string' &&
      message.includes('ReactDOM.render is deprecated')
    ) {
      return;
    }
    originalConsole.error(message, ...args);
  },
};