import { describe, it, expect } from 'vitest';
import JSZip from 'jszip';

/**
 * Tests for client-side ZIP parsing and data processing logic.
 *
 * These tests verify the same logic used in dist/index.html's
 * analyzeBtn click handler (JSZip parsing, set operations).
 */

// Extract the pure logic functions that mirror the client-side code
function parseFollowing(followingJson) {
  return new Set(
    (followingJson.relationships_following || [])
      .map((item) => {
        const fromStringList = (item.string_list_data || [])[0]?.value;
        return fromStringList || item.title;
      })
      .filter(Boolean),
  );
}

function parseFollowers(followersJson) {
  return new Set(
    followersJson
      .flatMap((item) => item.string_list_data || [])
      .map((entry) => entry.value)
      .filter(Boolean),
  );
}

function computeNonFollowers(followingSet, followersSet) {
  return [...followingSet].filter((username) => !followersSet.has(username)).sort();
}

function computeMutualCount(followingSet, followersSet) {
  return [...followingSet].filter((username) => followersSet.has(username)).length;
}

async function createTestZip(followingData, followersData) {
  const zip = new JSZip();
  zip.file('connections/followers_and_following/following.json', JSON.stringify(followingData));
  zip.file('connections/followers_and_following/followers_1.json', JSON.stringify(followersData));
  return zip.generateAsync({ type: 'arraybuffer' });
}

function parseAllFollowersFromZip(zip) {
  const followerFiles = Object.keys(zip.files)
    .filter((name) => name.match(/^connections\/followers_and_following\/followers_\d+\.json$/))
    .sort();
  return followerFiles;
}

async function parseFollowersFromMultipleFiles(zip, filePaths) {
  const followersSet = new Set();
  for (const filePath of filePaths) {
    const json = JSON.parse(await zip.file(filePath).async('string'));
    json
      .flatMap((item) => item.string_list_data || [])
      .map((entry) => entry.value)
      .filter(Boolean)
      .forEach((username) => followersSet.add(username));
  }
  return followersSet;
}

describe('following.json parsing', () => {
  it('extracts usernames from relationships_following', () => {
    const json = {
      relationships_following: [{ title: 'user1' }, { title: 'user2' }, { title: 'user3' }],
    };

    const result = parseFollowing(json);

    expect(result.size).toBe(3);
    expect(result.has('user1')).toBe(true);
    expect(result.has('user2')).toBe(true);
    expect(result.has('user3')).toBe(true);
  });

  it('handles empty relationships_following', () => {
    const json = { relationships_following: [] };

    expect(parseFollowing(json).size).toBe(0);
  });

  it('handles missing relationships_following key', () => {
    const json = {};

    expect(parseFollowing(json).size).toBe(0);
  });

  it('filters out null/undefined titles', () => {
    const json = {
      relationships_following: [
        { title: 'valid_user' },
        { title: null },
        { title: undefined },
        { title: '' },
        {},
      ],
    };

    const result = parseFollowing(json);

    expect(result.size).toBe(1);
    expect(result.has('valid_user')).toBe(true);
  });

  it('deduplicates usernames', () => {
    const json = {
      relationships_following: [{ title: 'user1' }, { title: 'user1' }],
    };

    expect(parseFollowing(json).size).toBe(1);
  });

  it('extracts username from string_list_data (new Instagram format)', () => {
    const json = {
      relationships_following: [
        {
          title: '',
          media_list_data: [],
          string_list_data: [
            { href: 'https://www.instagram.com/aunthk', value: 'aunthk', timestamp: 1234567890 },
          ],
        },
        {
          title: '',
          media_list_data: [],
          string_list_data: [
            {
              href: 'https://www.instagram.com/testuser',
              value: 'testuser',
              timestamp: 1234567890,
            },
          ],
        },
      ],
    };

    const result = parseFollowing(json);

    expect(result.size).toBe(2);
    expect(result.has('aunthk')).toBe(true);
    expect(result.has('testuser')).toBe(true);
  });

  it('prefers string_list_data over title when both exist', () => {
    const json = {
      relationships_following: [
        {
          title: 'Display Name',
          string_list_data: [{ value: 'actual_username', href: '', timestamp: 0 }],
        },
      ],
    };

    const result = parseFollowing(json);

    expect(result.size).toBe(1);
    expect(result.has('actual_username')).toBe(true);
    expect(result.has('Display Name')).toBe(false);
  });

  it('falls back to title when string_list_data is missing (old format)', () => {
    const json = {
      relationships_following: [{ title: 'old_format_user' }],
    };

    const result = parseFollowing(json);

    expect(result.size).toBe(1);
    expect(result.has('old_format_user')).toBe(true);
  });

  it('handles mixed old and new format entries', () => {
    const json = {
      relationships_following: [
        { title: 'old_user' },
        {
          title: '',
          string_list_data: [{ value: 'new_user', href: '', timestamp: 0 }],
        },
        {
          title: 'Display Name',
          string_list_data: [{ value: 'real_username', href: '', timestamp: 0 }],
        },
      ],
    };

    const result = parseFollowing(json);

    expect(result.size).toBe(3);
    expect(result.has('old_user')).toBe(true);
    expect(result.has('new_user')).toBe(true);
    expect(result.has('real_username')).toBe(true);
    expect(result.has('Display Name')).toBe(false);
  });

  it('handles empty string_list_data array', () => {
    const json = {
      relationships_following: [{ title: 'fallback_user', string_list_data: [] }],
    };

    const result = parseFollowing(json);

    expect(result.size).toBe(1);
    expect(result.has('fallback_user')).toBe(true);
  });
});

describe('followers_1.json parsing', () => {
  it('extracts usernames from string_list_data', () => {
    const json = [
      { string_list_data: [{ value: 'follower1' }] },
      { string_list_data: [{ value: 'follower2' }] },
    ];

    const result = parseFollowers(json);

    expect(result.size).toBe(2);
    expect(result.has('follower1')).toBe(true);
    expect(result.has('follower2')).toBe(true);
  });

  it('handles multiple values in one entry', () => {
    const json = [
      {
        string_list_data: [{ value: 'follower1' }, { value: 'follower2' }],
      },
    ];

    const result = parseFollowers(json);

    expect(result.size).toBe(2);
  });

  it('handles empty array', () => {
    expect(parseFollowers([]).size).toBe(0);
  });

  it('handles entries without string_list_data', () => {
    const json = [{ string_list_data: [{ value: 'follower1' }] }, {}, { other_field: 'ignored' }];

    const result = parseFollowers(json);

    expect(result.size).toBe(1);
    expect(result.has('follower1')).toBe(true);
  });

  it('filters out empty/null values', () => {
    const json = [
      {
        string_list_data: [{ value: 'valid' }, { value: '' }, { value: null }, {}],
      },
    ];

    const result = parseFollowers(json);

    expect(result.size).toBe(1);
    expect(result.has('valid')).toBe(true);
  });
});

describe('non-followers computation', () => {
  it('returns users in following but not in followers', () => {
    const following = new Set(['a', 'b', 'c', 'd']);
    const followers = new Set(['a', 'c', 'e']);

    const result = computeNonFollowers(following, followers);

    expect(result).toEqual(['b', 'd']);
  });

  it('returns empty array when everyone follows back', () => {
    const following = new Set(['a', 'b']);
    const followers = new Set(['a', 'b', 'c']);

    expect(computeNonFollowers(following, followers)).toEqual([]);
  });

  it('returns all following when no one follows back', () => {
    const following = new Set(['a', 'b']);
    const followers = new Set(['c', 'd']);

    expect(computeNonFollowers(following, followers)).toEqual(['a', 'b']);
  });

  it('returns sorted results', () => {
    const following = new Set(['zeta', 'alpha', 'mike']);
    const followers = new Set([]);

    expect(computeNonFollowers(following, followers)).toEqual(['alpha', 'mike', 'zeta']);
  });

  it('handles empty sets', () => {
    expect(computeNonFollowers(new Set(), new Set())).toEqual([]);
    expect(computeNonFollowers(new Set(['a']), new Set())).toEqual(['a']);
    expect(computeNonFollowers(new Set(), new Set(['a']))).toEqual([]);
  });
});

describe('mutual count computation', () => {
  it('counts mutual follows', () => {
    const following = new Set(['a', 'b', 'c', 'd']);
    const followers = new Set(['a', 'c', 'e']);

    expect(computeMutualCount(following, followers)).toBe(2);
  });

  it('returns 0 when no mutual follows', () => {
    const following = new Set(['a']);
    const followers = new Set(['b']);

    expect(computeMutualCount(following, followers)).toBe(0);
  });

  it('handles empty sets', () => {
    expect(computeMutualCount(new Set(), new Set())).toBe(0);
  });
});

describe('ZIP file parsing integration', () => {
  it('parses a valid Instagram ZIP file', async () => {
    const followingData = {
      relationships_following: [{ title: 'user_a' }, { title: 'user_b' }, { title: 'user_c' }],
    };
    const followersData = [
      { string_list_data: [{ value: 'user_a' }] },
      { string_list_data: [{ value: 'user_d' }] },
    ];

    const zipBuffer = await createTestZip(followingData, followersData);
    const zip = await JSZip.loadAsync(zipBuffer);

    const followingFile = zip.file('connections/followers_and_following/following.json');
    const followersFile = zip.file('connections/followers_and_following/followers_1.json');

    expect(followingFile).not.toBeNull();
    expect(followersFile).not.toBeNull();

    const followingJson = JSON.parse(await followingFile.async('string'));
    const followersJson = JSON.parse(await followersFile.async('string'));

    const followingSet = parseFollowing(followingJson);
    const followersSet = parseFollowers(followersJson);

    expect(followingSet.size).toBe(3);
    expect(followersSet.size).toBe(2);

    const nonFollowers = computeNonFollowers(followingSet, followersSet);
    expect(nonFollowers).toEqual(['user_b', 'user_c']);

    const mutual = computeMutualCount(followingSet, followersSet);
    expect(mutual).toBe(1);
  });

  it('handles ZIP without following.json', async () => {
    const zip = new JSZip();
    zip.file('some_other_file.json', '{}');
    const zipBuffer = await zip.generateAsync({ type: 'arraybuffer' });

    const loaded = await JSZip.loadAsync(zipBuffer);
    const followingFile = loaded.file('connections/followers_and_following/following.json');

    expect(followingFile).toBeNull();
  });

  it('handles ZIP without followers_1.json', async () => {
    const zip = new JSZip();
    zip.file(
      'connections/followers_and_following/following.json',
      JSON.stringify({
        relationships_following: [{ title: 'user1' }],
      }),
    );
    const zipBuffer = await zip.generateAsync({ type: 'arraybuffer' });

    const loaded = await JSZip.loadAsync(zipBuffer);
    const followersFile = loaded.file('connections/followers_and_following/followers_1.json');

    expect(followersFile).toBeNull();
  });

  it('parses multiple followers files (followers_1, followers_2, etc.)', async () => {
    const zip = new JSZip();
    zip.file(
      'connections/followers_and_following/following.json',
      JSON.stringify({
        relationships_following: [
          { title: 'user_a' },
          { title: 'user_b' },
          { title: 'user_c' },
          { title: 'user_d' },
        ],
      }),
    );
    zip.file(
      'connections/followers_and_following/followers_1.json',
      JSON.stringify([{ string_list_data: [{ value: 'user_a' }, { value: 'user_b' }] }]),
    );
    zip.file(
      'connections/followers_and_following/followers_2.json',
      JSON.stringify([{ string_list_data: [{ value: 'user_c' }] }]),
    );
    const zipBuffer = await zip.generateAsync({ type: 'arraybuffer' });
    const loaded = await JSZip.loadAsync(zipBuffer);

    const followerFiles = parseAllFollowersFromZip(loaded);
    expect(followerFiles).toEqual([
      'connections/followers_and_following/followers_1.json',
      'connections/followers_and_following/followers_2.json',
    ]);

    const followersSet = await parseFollowersFromMultipleFiles(loaded, followerFiles);
    expect(followersSet.size).toBe(3);
    expect(followersSet.has('user_a')).toBe(true);
    expect(followersSet.has('user_b')).toBe(true);
    expect(followersSet.has('user_c')).toBe(true);

    const followingJson = JSON.parse(
      await loaded.file('connections/followers_and_following/following.json').async('string'),
    );
    const followingSet = parseFollowing(followingJson);
    const nonFollowers = computeNonFollowers(followingSet, followersSet);
    expect(nonFollowers).toEqual(['user_d']);
  });

  it('ignores non-follower files in the directory', async () => {
    const zip = new JSZip();
    zip.file(
      'connections/followers_and_following/followers_1.json',
      JSON.stringify([{ string_list_data: [{ value: 'user_a' }] }]),
    );
    zip.file('connections/followers_and_following/following.json', JSON.stringify({}));
    zip.file('connections/followers_and_following/close_friends.json', JSON.stringify([]));
    const zipBuffer = await zip.generateAsync({ type: 'arraybuffer' });
    const loaded = await JSZip.loadAsync(zipBuffer);

    const followerFiles = parseAllFollowersFromZip(loaded);
    expect(followerFiles).toEqual(['connections/followers_and_following/followers_1.json']);
  });

  it('handles large follower/following lists', async () => {
    const following = Array.from({ length: 500 }, (_, i) => ({
      title: `user_${String(i).padStart(4, '0')}`,
    }));
    const followers = Array.from({ length: 300 }, (_, i) => ({
      string_list_data: [{ value: `user_${String(i).padStart(4, '0')}` }],
    }));

    const followingData = { relationships_following: following };
    const zipBuffer = await createTestZip(followingData, followers);

    const zip = await JSZip.loadAsync(zipBuffer);
    const followingJson = JSON.parse(
      await zip.file('connections/followers_and_following/following.json').async('string'),
    );
    const followersJson = JSON.parse(
      await zip.file('connections/followers_and_following/followers_1.json').async('string'),
    );

    const followingSet = parseFollowing(followingJson);
    const followersSet = parseFollowers(followersJson);
    const nonFollowers = computeNonFollowers(followingSet, followersSet);

    expect(followingSet.size).toBe(500);
    expect(followersSet.size).toBe(300);
    expect(nonFollowers.length).toBe(200);
  });
});

describe('username validation', () => {
  const usernameRegex = /^[a-zA-Z0-9._]+$/;

  it('accepts valid Instagram usernames', () => {
    expect(usernameRegex.test('instagram')).toBe(true);
    expect(usernameRegex.test('user.name')).toBe(true);
    expect(usernameRegex.test('user_name')).toBe(true);
    expect(usernameRegex.test('user123')).toBe(true);
    expect(usernameRegex.test('a.b_c.1')).toBe(true);
  });

  it('rejects invalid usernames', () => {
    expect(usernameRegex.test('')).toBe(false);
    expect(usernameRegex.test('user name')).toBe(false);
    expect(usernameRegex.test('user@name')).toBe(false);
    expect(usernameRegex.test('user<script>')).toBe(false);
    expect(usernameRegex.test("user'name")).toBe(false);
    expect(usernameRegex.test('user"name')).toBe(false);
  });
});
