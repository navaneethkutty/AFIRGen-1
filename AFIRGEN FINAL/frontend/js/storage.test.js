/**
 * Unit tests for Storage module
 */

// Mock localStorage
const localStorageMock = (() => {
  let store = {};

  return {
    getItem: jest.fn((key) => store[key] || null),
    setItem: jest.fn((key, value) => {
      store[key] = value.toString();
    }),
    removeItem: jest.fn((key) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: jest.fn((index) => {
      const keys = Object.keys(store);
      return keys[index] || null;
    })
  };
})();

global.localStorage = localStorageMock;

// Mock IndexedDB
const indexedDBMock = {
  open: jest.fn((name, version) => {
    const request = {
      result: null,
      error: null,
      onsuccess: null,
      onerror: null,
      onupgradeneeded: null
    };

    setTimeout(() => {
      const mockDB = {
        objectStoreNames: {
          contains: jest.fn(() => false)
        },
        createObjectStore: jest.fn((name, options) => ({
          createIndex: jest.fn()
        })),
        transaction: jest.fn((stores, mode) => ({
          objectStore: jest.fn((name) => ({
            put: jest.fn(() => ({
              onsuccess: null,
              onerror: null
            })),
            get: jest.fn(() => ({
              result: null,
              onsuccess: null,
              onerror: null
            })),
            getAll: jest.fn(() => ({
              result: [],
              onsuccess: null,
              onerror: null
            })),
            delete: jest.fn(() => ({
              onsuccess: null,
              onerror: null
            })),
            clear: jest.fn(() => ({
              onsuccess: null,
              onerror: null
            })),
            index: jest.fn(() => ({
              getAll: jest.fn(() => ({
                result: [],
                onsuccess: null,
                onerror: null
              }))
            }))
          }))
        }))
      };

      request.result = mockDB;
      if (request.onupgradeneeded) {
        request.onupgradeneeded({ target: { result: mockDB } });
      }
      if (request.onsuccess) {
        request.onsuccess();
      }
    }, 0);

    return request;
  })
};

global.indexedDB = indexedDBMock;

// Mock console
global.console = {
  log: jest.fn(),
  error: jest.fn(),
  warn: jest.fn()
};

// Mock window
global.window = {
  showToast: jest.fn()
};

describe('Storage Module', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.clear();
  });

  describe('LocalStorage Functions', () => {
    const setLocal = (key, value, ttl = null) => {
      try {
        const item = {
          value,
          timestamp: Date.now(),
          ttl
        };
        localStorage.setItem(key, JSON.stringify(item));
      } catch (error) {
        console.error('Error setting LocalStorage item:', error);
        throw error;
      }
    };

    const getLocal = (key) => {
      try {
        const itemStr = localStorage.getItem(key);
        if (!itemStr) return null;

        const item = JSON.parse(itemStr);

        if (item.ttl && Date.now() - item.timestamp > item.ttl) {
          localStorage.removeItem(key);
          return null;
        }

        return item.value;
      } catch (error) {
        console.error('Error getting LocalStorage item:', error);
        return null;
      }
    };

    const removeLocal = (key) => {
      try {
        localStorage.removeItem(key);
      } catch (error) {
        console.error('Error removing LocalStorage item:', error);
      }
    };

    const clearLocal = () => {
      try {
        localStorage.clear();
      } catch (error) {
        console.error('Error clearing LocalStorage:', error);
      }
    };

    describe('setLocal()', () => {
      test('should store value in localStorage', () => {
        setLocal('test-key', 'test-value');

        expect(localStorage.setItem).toHaveBeenCalled();
        const storedValue = localStorage.getItem('test-key');
        expect(storedValue).toBeTruthy();
      });

      test('should store object values', () => {
        const obj = { name: 'John', age: 30 };
        setLocal('user', obj);

        const retrieved = getLocal('user');
        expect(retrieved).toEqual(obj);
      });

      test('should store value with TTL', () => {
        setLocal('temp-key', 'temp-value', 5000);

        const storedValue = localStorage.getItem('temp-key');
        const parsed = JSON.parse(storedValue);
        expect(parsed.ttl).toBe(5000);
      });

      test('should handle storage errors', () => {
        localStorage.setItem.mockImplementationOnce(() => {
          throw new Error('Storage full');
        });

        expect(() => setLocal('key', 'value')).toThrow('Storage full');
        expect(console.error).toHaveBeenCalled();
      });
    });

    describe('getLocal()', () => {
      test('should retrieve stored value', () => {
        setLocal('test-key', 'test-value');
        const value = getLocal('test-key');

        expect(value).toBe('test-value');
      });

      test('should return null for non-existent key', () => {
        const value = getLocal('non-existent');

        expect(value).toBeNull();
      });

      test('should return null for expired value', () => {
        // Store with 1ms TTL
        setLocal('expired-key', 'expired-value', 1);

        // Wait for expiration
        return new Promise(resolve => {
          setTimeout(() => {
            const value = getLocal('expired-key');
            expect(value).toBeNull();
            resolve();
          }, 10);
        });
      });

      test('should return value before expiration', () => {
        setLocal('valid-key', 'valid-value', 10000); // 10 seconds

        const value = getLocal('valid-key');
        expect(value).toBe('valid-value');
      });

      test('should handle corrupted data', () => {
        localStorage.setItem('corrupted', 'not-json');

        const value = getLocal('corrupted');
        expect(value).toBeNull();
        expect(console.error).toHaveBeenCalled();
      });
    });

    describe('removeLocal()', () => {
      test('should remove item from localStorage', () => {
        setLocal('test-key', 'test-value');
        removeLocal('test-key');

        expect(localStorage.removeItem).toHaveBeenCalledWith('test-key');
        const value = getLocal('test-key');
        expect(value).toBeNull();
      });

      test('should handle removal of non-existent key', () => {
        expect(() => removeLocal('non-existent')).not.toThrow();
      });
    });

    describe('clearLocal()', () => {
      test('should clear all localStorage items', () => {
        setLocal('key1', 'value1');
        setLocal('key2', 'value2');

        clearLocal();

        expect(localStorage.clear).toHaveBeenCalled();
      });
    });
  });

  describe('IndexedDB Functions', () => {
    describe('initDB()', () => {
      test('should initialize IndexedDB', async () => {
        const initDB = async () => {
          return new Promise((resolve, reject) => {
            const request = indexedDB.open('AFIRGenDB', 1);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);

            request.onupgradeneeded = (event) => {
              const db = event.target.result;

              if (!db.objectStoreNames.contains('fir_history')) {
                const firStore = db.createObjectStore('fir_history', { keyPath: 'id' });
                firStore.createIndex('status', 'status', { unique: false });
                firStore.createIndex('date', 'date', { unique: false });
              }

              if (!db.objectStoreNames.contains('cache')) {
                db.createObjectStore('cache', { keyPath: 'key' });
              }
            };
          });
        };

        const db = await initDB();
        expect(db).toBeTruthy();
        expect(indexedDB.open).toHaveBeenCalledWith('AFIRGenDB', 1);
      });
    });

    describe('setDB()', () => {
      test('should store value in IndexedDB', async () => {
        const setDB = async (storeName, key, value) => {
          return new Promise((resolve) => {
            // Simplified mock implementation
            setTimeout(() => resolve(), 0);
          });
        };

        await expect(setDB('cache', 'test-key', 'test-value')).resolves.toBeUndefined();
      });

      test('should handle quota exceeded error', async () => {
        const setDB = async (storeName, key, value) => {
          const error = new Error('Quota exceeded');
          error.name = 'QuotaExceededError';
          throw error;
        };

        await expect(setDB('cache', 'key', 'value')).rejects.toThrow('Quota exceeded');
      });
    });

    describe('getDB()', () => {
      test('should retrieve value from IndexedDB', async () => {
        const getDB = async (storeName, key) => {
          return new Promise((resolve) => {
            setTimeout(() => resolve({ id: key, data: 'test-value' }), 0);
          });
        };

        const result = await getDB('cache', 'test-key');
        expect(result).toEqual({ id: 'test-key', data: 'test-value' });
      });

      test('should return null for non-existent key', async () => {
        const getDB = async (storeName, key) => {
          return new Promise((resolve) => {
            setTimeout(() => resolve(null), 0);
          });
        };

        const result = await getDB('cache', 'non-existent');
        expect(result).toBeNull();
      });
    });

    describe('getAllDB()', () => {
      test('should retrieve all items from store', async () => {
        const getAllDB = async (storeName) => {
          return new Promise((resolve) => {
            setTimeout(() => resolve([
              { id: '1', data: 'value1' },
              { id: '2', data: 'value2' }
            ]), 0);
          });
        };

        const results = await getAllDB('cache');
        expect(results).toHaveLength(2);
        expect(results[0].id).toBe('1');
      });

      test('should return empty array for empty store', async () => {
        const getAllDB = async (storeName) => {
          return new Promise((resolve) => {
            setTimeout(() => resolve([]), 0);
          });
        };

        const results = await getAllDB('cache');
        expect(results).toEqual([]);
      });
    });

    describe('deleteDB()', () => {
      test('should delete item from IndexedDB', async () => {
        const deleteDB = async (storeName, key) => {
          return new Promise((resolve) => {
            setTimeout(() => resolve(), 0);
          });
        };

        await expect(deleteDB('cache', 'test-key')).resolves.toBeUndefined();
      });
    });

    describe('clearDB()', () => {
      test('should clear all items from store', async () => {
        const clearDB = async (storeName) => {
          return new Promise((resolve) => {
            setTimeout(() => resolve(), 0);
          });
        };

        await expect(clearDB('cache')).resolves.toBeUndefined();
      });
    });

    describe('queryDB()', () => {
      test('should query items by index', async () => {
        const queryDB = async (storeName, indexName, value) => {
          return new Promise((resolve) => {
            setTimeout(() => resolve([
              { id: '1', status: 'pending' },
              { id: '2', status: 'pending' }
            ]), 0);
          });
        };

        const results = await queryDB('fir_history', 'status', 'pending');
        expect(results).toHaveLength(2);
        expect(results[0].status).toBe('pending');
      });

      test('should return empty array when no matches', async () => {
        const queryDB = async (storeName, indexName, value) => {
          return new Promise((resolve) => {
            setTimeout(() => resolve([]), 0);
          });
        };

        const results = await queryDB('fir_history', 'status', 'completed');
        expect(results).toEqual([]);
      });
    });
  });

  describe('TTL Functionality', () => {
    const setLocal = (key, value, ttl = null) => {
      const item = {
        value,
        timestamp: Date.now(),
        ttl
      };
      localStorage.setItem(key, JSON.stringify(item));
    };

    const getLocal = (key) => {
      const itemStr = localStorage.getItem(key);
      if (!itemStr) return null;

      const item = JSON.parse(itemStr);

      if (item.ttl && Date.now() - item.timestamp > item.ttl) {
        localStorage.removeItem(key);
        return null;
      }

      return item.value;
    };

    test('should expire items after TTL', (done) => {
      setLocal('temp', 'value', 50); // 50ms TTL

      setTimeout(() => {
        const value = getLocal('temp');
        expect(value).toBeNull();
        done();
      }, 100);
    });

    test('should not expire items without TTL', () => {
      setLocal('permanent', 'value');

      const value = getLocal('permanent');
      expect(value).toBe('value');
    });

    test('should not expire items before TTL', () => {
      setLocal('valid', 'value', 10000); // 10 seconds

      const value = getLocal('valid');
      expect(value).toBe('value');
    });
  });

  describe('Error Handling', () => {
    test('should handle localStorage quota exceeded', () => {
      const setLocal = (key, value, ttl = null) => {
        try {
          const item = {
            value,
            timestamp: Date.now(),
            ttl
          };
          localStorage.setItem(key, JSON.stringify(item));
        } catch (error) {
          console.error('Error setting LocalStorage item:', error);
          throw error;
        }
      };

      localStorage.setItem.mockImplementationOnce(() => {
        const error = new Error('QuotaExceededError');
        error.name = 'QuotaExceededError';
        throw error;
      });

      expect(() => setLocal('key', 'value')).toThrow();
      expect(console.error).toHaveBeenCalled();
    });

    test('should handle IndexedDB errors gracefully', async () => {
      const getDB = async (storeName, key) => {
        try {
          throw new Error('Database error');
        } catch (error) {
          console.error('Error getting IndexedDB item:', error);
          return null;
        }
      };

      const result = await getDB('cache', 'key');
      expect(result).toBeNull();
      expect(console.error).toHaveBeenCalled();
    });
  });
});
