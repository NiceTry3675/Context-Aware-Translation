/**
 * IndexedDB storage wrapper for illustrations
 * Handles client-side storage of illustration data when ILLUSTRATIONS_TO_USER_SIDE is enabled
 */

interface StoredIllustration {
  jobId: string;
  segmentIndex: number;
  data: string; // base64 encoded image or prompt JSON
  type: 'image' | 'prompt';
  mimeType?: string;
  timestamp: number;
  size: number; // in bytes
}

class IllustrationStorage {
  private dbName = 'IllustrationDB';
  private dbVersion = 1;
  private storeName = 'illustrations';
  private db: IDBDatabase | null = null;
  private maxStorageSize = 500 * 1024 * 1024; // 500MB limit
  private maxAge = 30 * 24 * 60 * 60 * 1000; // 30 days

  /**
   * Initialize the IndexedDB database
   */
  async init(): Promise<void> {
    if (this.db) return;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onerror = () => {
        console.error('Failed to open IndexedDB:', request.error);
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // Create object store if it doesn't exist
        if (!db.objectStoreNames.contains(this.storeName)) {
          const objectStore = db.createObjectStore(this.storeName, {
            keyPath: ['jobId', 'segmentIndex']
          });

          // Create indexes for efficient querying
          objectStore.createIndex('jobId', 'jobId', { unique: false });
          objectStore.createIndex('timestamp', 'timestamp', { unique: false });
          objectStore.createIndex('size', 'size', { unique: false });
        }
      };
    });
  }

  /**
   * Store an illustration in IndexedDB
   */
  async storeIllustration(
    jobId: string,
    segmentIndex: number,
    data: any,
    type: 'image' | 'prompt'
  ): Promise<void> {
    await this.init();

    // Convert data to storable format
    let dataStr: string;
    let size: number;
    let mimeType: string | undefined;

    if (type === 'image' && typeof data === 'object' && data.data) {
      // Base64 image data
      dataStr = data.data;
      mimeType = data.mime_type || 'image/png';
      size = Math.ceil((dataStr.length * 3) / 4); // Estimate base64 size
    } else {
      // Prompt or other JSON data
      dataStr = JSON.stringify(data);
      size = new Blob([dataStr]).size;
    }

    // Check storage limits before storing
    await this.enforceStorageLimits(size);

    const illustration: StoredIllustration = {
      jobId,
      segmentIndex,
      data: dataStr,
      type,
      mimeType,
      timestamp: Date.now(),
      size
    };

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.put(illustration);

      request.onsuccess = () => resolve();
      request.onerror = () => {
        console.error('Failed to store illustration:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Retrieve an illustration from IndexedDB
   */
  async getIllustration(
    jobId: string,
    segmentIndex: number
  ): Promise<StoredIllustration | null> {
    await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.get([jobId, segmentIndex]);

      request.onsuccess = () => {
        const result = request.result;
        if (result) {
          // Check if data is expired
          if (Date.now() - result.timestamp > this.maxAge) {
            this.deleteIllustration(jobId, segmentIndex);
            resolve(null);
          } else {
            resolve(result);
          }
        } else {
          resolve(null);
        }
      };

      request.onerror = () => {
        console.error('Failed to get illustration:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Retrieve all stored illustrations
   */
  async getAllItems(): Promise<StoredIllustration[]> {
    await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.getAll();

      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Get all illustrations for a job
   */
  async getJobIllustrations(jobId: string): Promise<StoredIllustration[]> {
    await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const index = store.index('jobId');
      const request = index.getAll(jobId);

      request.onsuccess = () => {
        const results = request.result || [];
        // Filter out expired items
        const validResults = results.filter(item =>
          Date.now() - item.timestamp <= this.maxAge
        );
        resolve(validResults);
      };

      request.onerror = () => {
        console.error('Failed to get job illustrations:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Delete an illustration from IndexedDB
   */
  async deleteIllustration(
    jobId: string,
    segmentIndex: number
  ): Promise<void> {
    await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.delete([jobId, segmentIndex]);

      request.onsuccess = () => resolve();
      request.onerror = () => {
        console.error('Failed to delete illustration:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Delete all illustrations for a job
   */
  async deleteJobIllustrations(jobId: string): Promise<void> {
    await this.init();

    const illustrations = await this.getJobIllustrations(jobId);

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);

      let deleteCount = 0;
      for (const ill of illustrations) {
        const request = store.delete([ill.jobId, ill.segmentIndex]);
        request.onsuccess = () => {
          deleteCount++;
          if (deleteCount === illustrations.length) {
            resolve();
          }
        };
        request.onerror = () => reject(request.error);
      }

      if (illustrations.length === 0) {
        resolve();
      }
    });
  }

  /**
   * Get storage statistics
   */
  async getStorageStats(): Promise<{
    totalSize: number;
    itemCount: number;
    oldestTimestamp: number;
    newestTimestamp: number;
  }> {
    await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.getAll();

      request.onsuccess = () => {
        const items = request.result || [];

        const stats = {
          totalSize: items.reduce((sum, item) => sum + item.size, 0),
          itemCount: items.length,
          oldestTimestamp: items.length > 0
            ? Math.min(...items.map(i => i.timestamp))
            : 0,
          newestTimestamp: items.length > 0
            ? Math.max(...items.map(i => i.timestamp))
            : 0
        };

        resolve(stats);
      };

      request.onerror = () => {
        console.error('Failed to get storage stats:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Enforce storage limits by removing old items if necessary
   */
  private async enforceStorageLimits(newItemSize: number): Promise<void> {
    const stats = await this.getStorageStats();

    if (stats.totalSize + newItemSize > this.maxStorageSize) {
      // Remove oldest items until we have enough space
      await this.cleanupOldItems(newItemSize);
    }

    // Also clean up expired items
    await this.cleanupExpiredItems();
  }

  /**
   * Clean up old items to make space
   */
  private async cleanupOldItems(requiredSpace: number): Promise<void> {
    await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const index = store.index('timestamp');
      const request = index.openCursor();

      let freedSpace = 0;

      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;

        if (cursor && freedSpace < requiredSpace) {
          const item = cursor.value;
          freedSpace += item.size;
          cursor.delete();
          cursor.continue();
        } else {
          resolve();
        }
      };

      request.onerror = () => {
        console.error('Failed to cleanup old items:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Clean up expired items
   */
  private async cleanupExpiredItems(): Promise<void> {
    await this.init();

    const cutoffTime = Date.now() - this.maxAge;

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const index = store.index('timestamp');
      const range = IDBKeyRange.upperBound(cutoffTime);
      const request = index.openCursor(range);

      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;

        if (cursor) {
          cursor.delete();
          cursor.continue();
        } else {
          resolve();
        }
      };

      request.onerror = () => {
        console.error('Failed to cleanup expired items:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Clear all stored illustrations
   */
  async clearAll(): Promise<void> {
    await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.clear();

      request.onsuccess = () => resolve();
      request.onerror = () => {
        console.error('Failed to clear all illustrations:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Convert base64 to blob URL for display
   */
  base64ToBlobUrl(base64: string, mimeType: string = 'image/png'): string {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);

    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }

    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: mimeType });

    return URL.createObjectURL(blob);
  }

  /**
   * Check if browser supports IndexedDB
   */
  isSupported(): boolean {
    return 'indexedDB' in window;
  }
}

// Export singleton instance
export const illustrationStorage = new IllustrationStorage();