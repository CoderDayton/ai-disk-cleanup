// Jest mock for Tauri API
export const invoke = jest.fn();
export const dialog = {
  ask: jest.fn(),
  confirm: jest.fn(),
  message: jest.fn(),
  open: jest.fn(),
  save: jest.fn()
};
export const fs = {
  exists: jest.fn(),
  readTextFile: jest.fn(),
  writeTextFile: jest.fn(),
  readDir: jest.fn(),
  createDir: jest.fn(),
  removeDir: jest.fn(),
  removeFile: jest.fn(),
  copyFile: jest.fn(),
  renameFile: jest.fn()
};
export const notification = {
  isPermissionGranted: jest.fn(),
  requestPermission: jest.fn(),
  send: jest.fn()
};
export const shell = {
  open: jest.fn()
};
export const os = {
  platform: jest.fn(),
  version: jest.fn(),
  arch: jest.fn(),
  type: jest.fn(),
  versionDetails: jest.fn()
};
export const window = {
  getCurrent: jest.fn(() => ({
    label: 'main',
    title: 'AI Disk Cleaner',
    url: 'http://localhost:1420',
    width: 1200,
    height: 800,
    x: 0,
    y: 0,
    theme: 'light',
    resizable: true,
    decorations: true,
    alwaysOnTop: false,
    skipTaskbar: false,
    center: true,
    maximized: false,
    minimized: false,
    focused: true,
    close: jest.fn(),
    hide: jest.fn(),
    show: jest.fn(),
    maximize: jest.fn(),
    minimize: jest.fn(),
    unmaximize: jest.fn(),
    unminimize: jest.fn(),
    startDragging: jest.fn(),
    setResizable: jest.fn(),
    setTitle: jest.fn(),
    setDecorations: jest.fn(),
    setAlwaysOnTop: jest.fn(),
    setSize: jest.fn(),
    setMinSize: jest.fn(),
    setMaxSize: jest.fn(),
    setPosition: jest.fn(),
    setFullscreen: jest.fn(),
    setFocus: jest.fn(),
    setIcon: jest.fn(),
    setSkipTaskbar: jest.fn(),
    setTheme: jest.fn(),
    centerSync: jest.fn(),
    centerAsync: jest.fn(),
    requestUserAttention: jest.fn(),
    setProgressBar: jest.fn(),
    setProgressBarState: jest.fn(),
    setVisibleOnAllWorkspaces: jest.fn(),
    setCursorGrab: jest.fn(),
    setCursorIcon: jest.fn(),
    setCursorPosition: jest.fn(),
    setIgnoreCursorEvents: jest.fn(),
    listen: jest.fn(),
    once: jest.fn(),
    emit: jest.fn()
  }))
};
export const app = {
  name: 'AI Disk Cleaner',
  version: '0.2.0',
  tauriVersion: '2.0.0',
  getGlobal: jest.fn(),
  setGlobal: jest.fn(),
  show: jest.fn(),
  hide: jest.fn()
};

// Mock @tauri-apps/api module
export default {
  invoke,
  dialog,
  fs,
  notification,
  shell,
  os,
  window,
  app
};