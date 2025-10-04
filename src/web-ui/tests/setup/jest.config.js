import { defaults } from 'jest-config';
import { pathsToModuleNameMapper } from 'ts-jest';
import { compilerOptions } from '../tsconfig.json';

/** @type {import('jest').Config} */
export default {
  // Use the built-in presets for TypeScript and React
  preset: 'ts-jest',
  testEnvironment: 'jsdom',

  // Setup files for test environment
  setupFilesAfterEnv: ['<rootDir>/tests/setup/tests-setup.ts'],

  // Module name mapping for TypeScript path aliases
  moduleNameMapping: pathsToModuleNameMapper(compilerOptions.paths, {
    prefix: '<rootDir>/src',
  }),

  // Transform configuration
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: 'tsconfig.json',
      useESM: true,
    }],
    '^.+\\.(js|jsx)$': 'babel-jest',
  },

  // Module file extensions
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],

  // Test match patterns
  testMatch: [
    '<rootDir>/tests/**/__tests__/**/*.(ts|tsx|js)',
    '<rootDir>/tests/**/*.test.(ts|tsx|js)',
    '<rootDir>/src/**/__tests__/**/*.(ts|tsx|js)',
    '<rootDir>/src/**/*.test.(ts|tsx|js)',
  ],

  // Ignore patterns
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/build/',
    '/.git/',
    '/coverage/',
  ],

  // Collect coverage from source files
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{ts,tsx}',
    '!src/**/index.ts',
  ],

  // Coverage configuration
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html', 'json-summary'],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },

  // Mock configuration
  clearMocks: true,
  restoreMocks: true,

  // Global variables
  globals: {
    'ts-jest': {
      useESM: true,
    },
  },

  // Extensions to transform
  moduleDirectories: ['node_modules', '<rootDir>/src'],

  // Transform ignore patterns for ESM modules
  transformIgnorePatterns: [
    'node_modules/(?!(@tauri-apps|@radix-ui|lucide-react)/)',
  ],

  // Mock CSS and asset files
  moduleNameMapping: {
    '^.+\\.module\\.(css|sass|scss)$': 'identity-obj-proxy',
    '^.+\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$': '<rootDir>/tests/setup/fileMock.js',
  },

  // Setup files
  setupFiles: ['<rootDir>/tests/setup/jest.polyfills.js'],

  // Test timeout
  testTimeout: 10000,

  // Verbose output
  verbose: true,

  // Watch plugins
  watchPlugins: [
    'jest-watch-typeahead/filename',
    'jest-watch-typeahead/testname',
  ],

  // Reporter configuration
  reporters: [
    'default',
    [
      'jest-junit',
      {
        outputDirectory: 'coverage',
        outputName: 'junit.xml',
      },
    ],
  ],

  // Error handling
  errorOnDeprecated: true,

  // Performance optimization
  maxWorkers: '50%',

  // Cache configuration
  cache: true,
  cacheDirectory: '<rootDir>/node_modules/.cache/jest',

  // Test environment options
  testEnvironmentOptions: {
    url: 'http://localhost:3000',
    resources: 'usable',
    runScripts: 'dangerously',
  },
};