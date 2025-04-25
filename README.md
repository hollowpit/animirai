
# Manga API

A FastAPI-based API server for retrieving manga information from various sources.

## Getting Started

The API server runs on port 3000. To start the server, click the "Run" button in the Replit interface.

## API Workflow

The typical workflow for using this API follows these steps:

1. **Get Available Sources** - Retrieve a list of all available manga sources
2. **Browse or Search Manga** - Get manga listings (popular, latest, or search results)
3. **Get Chapter Details** - Retrieve pages for a specific chapter

## API Endpoints

### Get Available Sources

```
GET /api/sources
```

Returns a list of all available manga sources.

#### Response Structure

```json
[
  {
    "name": "MangaDex",
    "url": "https://mangadex.org"
  },
  {
    "name": "Comick",
    "url": "https://comick.io"
  },
  ...
]
```

### Get Popular Manga

```
GET /api/manga/popular?source={source_name}&page={page_number}
```

Parameters:
- `source`: Name of the manga source (e.g., "mangadex", "comick")
- `page`: Page number for pagination (default: 1)

#### Response Structure

```json
[
  {
    "title": "Manga Title",
    "author": "Author Name",
    "description": "Manga description...",
    "poster": "https://url-to-cover-image.jpg",
    "total_chapters": 42,
    "tags": ["Tag1", "Tag2"],
    "genres": ["Genre1", "Genre2"],
    "status": "Ongoing",
    "rating": 4.7,
    "url": "/manga/manga-id",
    "chapter_ids": {
      "Chapter 1": "chapter-id-1",
      "Chapter 2": "chapter-id-2"
    }
  },
  ...
]
```

### Get Latest Manga

```
GET /api/manga/latest?source={source_name}&page={page_number}
```

Parameters:
- `source`: Name of the manga source (e.g., "mangadex", "comick")
- `page`: Page number for pagination (default: 1)

Response structure is the same as the popular manga endpoint.

### Search Manga

```
GET /api/manga/search?source={source_name}&q={search_query}&page={page_number}
```

Parameters:
- `source`: Name of the manga source (e.g., "mangadex", "comick")
- `q`: Search query string
- `page`: Page number for pagination (default: 1)

Response structure is the same as the popular manga endpoint.

### Get Chapter Pages

```
GET /api/manga/chapter?source={source_name}&id={chapter_id}
```

Parameters:
- `source`: Name of the manga source (e.g., "mangadex", "comick")
- `id`: Chapter ID

#### Response Structure

```json
{
  "id": "chapter-id",
  "title": "Chapter Title",
  "total_pages": 24,
  "pages": [
    "https://url-to-page-1.jpg",
    "https://url-to-page-2.jpg",
    ...
  ]
}
```

## Workflow Examples

### Example 1: Browsing Popular Manga

1. Get all available sources:
   ```
   GET /api/sources
   ```

2. Browse popular manga from MangaDex (first page):
   ```
   GET /api/manga/popular?source=mangadex&page=1
   ```

3. Get pages for a specific chapter:
   ```
   GET /api/manga/chapter?source=mangadex&id=chapter-id
   ```

### Example 2: Searching for Manga

1. Search for "One Piece" on Comick:
   ```
   GET /api/manga/search?source=comick&q=One%20Piece&page=1
   ```

2. Browse through the chapter list in the response

3. Get the pages for a specific chapter:
   ```
   GET /api/manga/chapter?source=comick&id=chapter-id
   ```

## Available Sources

The API currently supports these manga sources:
- MangaDex
- Comick
- Toonily
- NHentai
- Hentai3

Each source may have different features and content availability.
