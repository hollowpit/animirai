
class Manga():
    def __init__(self, title, author, description, poster, chapters, chapter_and_pages: dict, tags=None, genres=None, status="Ongoing", rating=-1):
        self.title = title
        self.author = author
        self.description = description
        self.poster = poster
        self.chapters = chapters
        self.chapter_and_pages = chapter_and_pages
        self.tags = tags
        self.genres = genres
        self.status = status
        self.rating = rating

    def _chapters_and_pages_model(self):
        """General Structure of the chapters and pages"""
        return {
            "chapters": [
                {
                    "title": "Chapter 1 - Name Of The Chapter",
                    "total_pages": 3,
                    "pages": ["page_url_1", "page_url_2"] # And so on.
                },
                {
                    "title": "Chapter 2 - Name Of The Chapter",
                    "total_pages": 3,
                    "pages": ["page_url_1", "page_url_2"]
                },
            ],
        }
            

class Anime():
    def __init__(self, title, description, poster, episodes, episode_and_videos: dict, tags=None, genres=None, status="Ongoing", rating=-1):
        self.title = title
        self.description = description
        self.poster = poster
        self.episodes = episodes
        self.episode_and_videos = episode_and_videos
        self.tags = tags
        self.genres = genres
        self.status = status
        self.rating = rating

    def _episodes_and_videos_model(self):
        """General Structure of the episodes and videos"""
        return {
            "episodes":
                {
                    "title": "Episode 1 - Name Of The Episode",
                    "total_episodes": 3,
                    "streaming_links": {
                        "1080p": "video_url_1",
                        "720p": "video_url_2",
                        "480p": "video_url_3",
                        "360p": "video_url_4",
                        "240p": "video_url_5",
                        "144p": "video_url_6",
                        "required": "Must have one quality or more"
                    }
                },
            ]
        }
