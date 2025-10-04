export function createMockFileSystem(structure: Record<string, any>) {
  return {
    exists: (path: string) => Promise.resolve(structure.hasOwnProperty(path)),
    readDir: (path: string) => {
      const items = Object.entries(structure)
        .filter(([key]) => key.startsWith(path + '/'))
        .map(([key, value]) => {
          const name = key.replace(path + '/', '');
          const parts = name.split('/');
          return parts.length === 1 ? { name, ...value } : null;
        })
        .filter(Boolean);
      return Promise.resolve(items);
    },
    readTextFile: (path: string) => {
      if (structure[path] && typeof structure[path] === 'string') {
        return Promise.resolve(structure[path]);
      }
      return Promise.reject(new Error(`File not found: ${path}`));
    },
    getFileInfo: (path: string) => {
      if (structure[path]) {
        return Promise.resolve(structure[path]);
      }
      return Promise.reject(new Error(`Path not found: ${path}`));
    },
  };
}

export function createMockFile(name: string, size: number, type = 'file') {
  return {
    name,
    path: `/mock/path/${name}`,
    size,
    type,
    modified: new Date(),
    created: new Date(),
    accessed: new Date(),
  };
}

export function createMockDirectory(name: string, files: any[] = []) {
  return {
    name,
    path: `/mock/path/${name}`,
    type: 'directory',
    size: files.reduce((acc, file) => acc + file.size, 0),
    files,
    modified: new Date(),
    created: new Date(),
    accessed: new Date(),
  };
}

export async function waitForCondition(
  condition: () => boolean,
  timeout = 5000,
  interval = 100
): Promise<void> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    if (condition()) {
      return;
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }

  throw new Error(`Condition not met within ${timeout}ms`);
}

export function measurePerformance<T>(
  name: string,
  fn: () => Promise<T> | T
): Promise<{ result: T; duration: number }> {
  const start = performance.now();
  const result = fn();

  if (result instanceof Promise) {
    return result.then(res => {
      const end = performance.now();
      const duration = end - start;
      console.log(`${name} took ${duration.toFixed(2)} milliseconds`);
      return { result: res, duration };
    });
  } else {
    const end = performance.now();
    const duration = end - start;
    console.log(`${name} took ${duration.toFixed(2)} milliseconds`);
    return Promise.resolve({ result, duration });
  }
}

export function createPerformanceThresholds() {
  return {
    responseTime: 100, // ms
    startupTime: 2000, // ms
    fileOperationTime: 500, // ms
    analysisTime: 10000, // ms
    cleanupTime: 5000, // ms
  };
}

export function validatePerformanceThresholds(
  metrics: Record<string, number>,
  thresholds: ReturnType<typeof createPerformanceThresholds>
): { passed: boolean; violations: string[] } {
  const violations: string[] = [];

  Object.entries(thresholds).forEach(([metric, threshold]) => {
    if (metrics[metric] && metrics[metric] > threshold) {
      violations.push(`${metric}: ${metrics[metric]}ms > ${threshold}ms`);
    }
  });

  return {
    passed: violations.length === 0,
    violations,
  };
}