import json
import re
import webbrowser

from bs4 import BeautifulSoup

from pyhub.mcptools import mcp
from pyhub.mcptools.music.types import Field, MusicServiceVendor, SongUid
from pyhub.mcptools.music.utils import get_number_from_string, get_response, remove_quotes

MELON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/60.0.3112.113 Safari/537.36"
    ),
    "Referer": "https://www.melon.com/index.htm",
}


@mcp.tool(experimental=True)
async def music_get_top100_songs(
    vendor: MusicServiceVendor = Field(
        description="Music service provider. Currently only supports MELON.",
        examples=["MusicServiceVendor.MELON"],
    )
) -> str:
    """Fetches the real-time TOP 100 chart information from a music streaming service.

    Retrieves the current TOP 100 songs chart from the specified music service,
    including detailed information about each song, artist, and album.

    Returns:
        str: JSON string containing TOP 100 songs list with the following fields for each song:
            - song_uid (int): Unique identifier for the song
            - rank (str): Current chart ranking
            - song_name (str): Title of the song
            - artist_uid (int): Unique identifier for the artist
            - artist_name (str): Name of the artist
            - album_uid (int): Unique identifier for the album
            - album_name (str): Name of the album
            - url (str): Direct link to the song's detail page
            - likes (int): Number of likes/hearts for the song

    Examples:
        >>> music_get_top100_songs(MusicServiceVendor.MELON)
        # Returns JSON string with top 100 songs from Melon

    Raises:
        ValueError: If an unsupported music service vendor is specified
    """

    if vendor == MusicServiceVendor.MELON:
        page_url = "https://www.melon.com/chart/index.htm"

        res = await get_response(page_url, headers=MELON_HEADERS)
        html = res.text

        # HTML 응답 문자열로부터, 필요한 태그 정보를 추출하기 위해, BeautifulSoup4 객체를 생성합니다.
        soup = BeautifulSoup(html, "html.parser")

        # BeautifulSoup4 객체를 통해 노래 정보를 추출해냅니다.
        song_list = []

        for song_tag in soup.select("#tb_list tbody tr, #pageList tbody tr"):
            play_song_tag = song_tag.select_one("a[href*=playSong]")
            song_name = play_song_tag.text
            __, song_uid = re.findall(r"\d+", play_song_tag["href"])
            song_uid = int(song_uid)

            artist_tag = song_tag.select_one("a[href*=goArtistDetail]")
            artist_name = artist_tag.text
            artist_uid = int(get_number_from_string(artist_tag["href"]))

            album_tag = song_tag.select_one("a[href*=goAlbumDetail]")
            album_uid = int(get_number_from_string(album_tag["href"]))
            album_name = album_tag["title"]
            rank = song_tag.select_one(".rank").text

            song = {
                "song_uid": song_uid,
                "rank": rank,
                "song_name": song_name,
                "artist_uid": artist_uid,
                "artist_name": artist_name,
                "album_uid": album_uid,
                "album_name": album_name,
                "url": f"https://www.melon.com/song/detail.htm?songId={song_uid}",
            }

            song_list.append(song)

        # 좋아요 수는 따로 요청해야합니다. 노래 id 목록을 인자로 넘깁니다.
        url = "https://www.melon.com/commonlike/getSongLike.json"
        params = {
            "contsIds": ", ".join(str(song["song_uid"]) for song in song_list),
        }
        res = await get_response(url, params=params, headers=MELON_HEADERS)
        like_dict = {int(song["CONTSID"]): song["SUMMCNT"] for song in res.json()["contsLike"]}

        for song in song_list:
            song["likes"] = like_dict[song["song_uid"]]

        return json.dumps(song_list, ensure_ascii=False)

    else:
        return f"Error: Unsupported music service vendor : {vendor}"


@mcp.tool(experimental=True)
async def music_search_songs(
    vendor: MusicServiceVendor = Field(
        description="Music service provider. Currently only supports MELON.",
        examples=["MusicServiceVendor.MELON"],
    ),
    query: str = Field(
        description="""Search query for song titles, artist names, or album names.
            For MELON, use only essential keywords instead of natural language.""",
        examples=["아이유 라일락", "라일락", "BTS Butter"],
    ),
) -> str:
    """Searches for songs, artists, and albums in a music streaming service.

    Performs a comprehensive search across songs, artists, and albums using the provided
    query string. Returns separate lists for matching songs, artists, and albums.

    Search Best Practices:
        1. Use only essential keywords (artist name, song title) for better results
        2. Natural language queries are not supported and may yield no results
        3. Best practice is to:
           - First search with artist name or song title
           - Then find the exact song from the returned song_list

    Returns:
        str: JSON string containing search results with three main sections:
            song_list: List of matching songs with fields:
                - song_uid (int): Unique identifier for the song
                - song_name (str): Title of the song
                - album_img_url (str): URL of the album cover image
                - album_uid (int): Unique identifier for the album
                - album_name (str): Name of the album
                - artist_uid (int): Unique identifier for the artist
                - artist_name (str): Name of the artist
                - url (str): Direct link to the song's detail page

            artist_list: List of matching artists with fields:
                - artist_uid (int): Unique identifier for the artist
                - artist_name (str): Name of the artist
                - artist_name_display (str): Display name of the artist
                - artist_img_url (str): URL of the artist image
                - nationality (str): Artist's nationality
                - gender (str): Artist's gender
                - act_type (str): Type of artist activity
                - url (str): Direct link to the artist's page

            album_list: List of matching albums with fields:
                - album_uid (int): Unique identifier for the album
                - album_name (str): Name of the album
                - album_name_display (str): Display name of the album
                - album_img_url (str): URL of the album cover image
                - artist_name (str): Name of the artist
                - release_date (str): Album release date
                - url (str): Direct link to the album's detail page

    Examples:
        >>> music_search_songs(MusicServiceVendor.MELON, "아이유 라일락")
        >>> music_search_songs(MusicServiceVendor.MELON, "BTS")
        >>> music_search_songs(MusicServiceVendor.MELON, "NewJeans")

    Raises:
        ValueError: If an unsupported music service vendor is specified
    """

    # LLM을 통한 인자에서 쌍따옴표/홑따옴표가 붙기도 합니다. 이를 제거하지 않으면 멜론에서 검색결과가 없습니다.
    query = remove_quotes(query)

    if vendor == MusicServiceVendor.MELON:
        url = "https://www.melon.com/search/keyword/index.json"
        jscallback = "_"
        params = {
            "jscallback": jscallback,
            "query": query,
        }

        res = await get_response(url, params=params, headers=MELON_HEADERS)
        jsonp_string = res.text

        json_string = jsonp_string.replace(f"{jscallback}(", "").replace(");", "")
        obj = json.loads(json_string)

        song_list = []
        for song_content in obj.get("SONGCONTENTS", []):
            song_uid = song_content["SONGID"]
            song_list.append(
                {
                    "song_uid": song_uid,
                    "song_name": song_content["SONGNAME"],
                    "album_img_url": song_content["ALBUMIMG"],
                    "album_uid": song_content["ALBUMID"],
                    "album_name": song_content["ALBUMNAME"],
                    "artist_uid": song_content["ARTISTID"],
                    "artist_name": song_content["ARTISTNAME"],
                    "url": f"https://www.melon.com/song/detail.htm?songId={song_uid}",
                }
            )

        artist_list = []
        for artist_content in obj.get("ARTISTCONTENTS", []):
            artist_uid = artist_content["ARTISTID"]
            artist_list.append(
                {
                    "artist_uid": artist_uid,
                    "artist_name": artist_content["ARTISTNAME"],
                    "artist_name_display": artist_content["ARTISTNAMEDP"],
                    "artist_img_url": artist_content["ARITSTIMG"],
                    "nationality": artist_content["NATIONALITYNAME"],
                    "gender": artist_content["SEX"],
                    "act_type": artist_content["ACTTYPENAMES"],
                    "url": f"https://www.melon.com/artist/timeline.htm?artistId={artist_uid}",
                }
            )

        album_list = []
        for album_content in obj.get("ALBUMCONTENTS", []):
            album_uid = album_content["ALBUMID"]
            album_list.append(
                {
                    "album_uid": album_uid,
                    "album_name": album_content["ALBUMNAME"],
                    "album_name_display": album_content["ALBUMNAMEDP"],
                    "album_img_url": album_content["ALBUMIMG"],
                    "artist_name": album_content["ARTISTNAME"],
                    "release_date": album_content["ISSUEDATE"],
                    "url": f"https://www.melon.com/album/detail.htm?albumId={album_uid}",
                }
            )

        return json.dumps(
            {
                "song_list": song_list,
                "artist_list": artist_list,
                "album_list": album_list,
            },
            ensure_ascii=False,
        )

    else:
        return f"Error: Unsupported music service vendor : {vendor}"


@mcp.tool(experimental=True)
async def music_get_song_detail(
    vendor: MusicServiceVendor = Field(
        description="Music service provider. Currently only supports MELON.",
        examples=["MusicServiceVendor.MELON"],
    ),
    song_uid: SongUid = Field(
        description="Unique identifier for the song to retrieve details for.",
        examples=["33487916", "35338198"],
    ),
) -> str:
    """Retrieves detailed information about a specific song from a music streaming service.

    Fetches comprehensive details about a song including its metadata, lyrics, and related
    information using the song's unique identifier.

    Returns:
        str: JSON string containing detailed song information with the following fields:
            - name (str): Title of the song
            - album_name (str): Name of the album
            - artist_name (str): Name of the artist
            - cover_url (str|None): URL of the album cover image
            - lyric (str): Song lyrics (maybe empty if not available)
            - genre (list[str]): List of genres
            - published_date (str|None): Release date in YYYY-MM-DD format

    Examples:
        >>> music_get_song_detail(MusicServiceVendor.MELON, "33487916")  # IU - 라일락
        >>> music_get_song_detail(MusicServiceVendor.MELON, "35338198")  # NewJeans - Super Shy

    Raises:
        ValueError: If an unsupported music service vendor is specified
        AttributeError: If the specified song is not found
    """

    if vendor == MusicServiceVendor.MELON:
        song_detail_url = f"https://www.melon.com/song/detail.htm?songId={song_uid}"

        res = await get_response(song_detail_url, headers=MELON_HEADERS)
        song_html = res.text
        soup = BeautifulSoup(song_html, "html.parser")

        for tag in soup.select(".none, img"):
            tag.extract()

        try:
            name = soup.select_one(".song_name").text.strip()
            album_name = soup.select_one("[href*=goAlbumDetail]").text.strip()
            artist_name = soup.select_one(".artist_name").text.strip()

            try:
                cover_url = soup.select_one(".section_info img")["src"].split("?", 1)[0]
            except TypeError:
                cover_url = None

            keys = [tag.text.strip() for tag in soup.select(".section_info .meta dt")]
            values = [tag.text.strip() for tag in soup.select(".section_info .meta dd")]
            meta_dict = dict(zip(keys, values, strict=False))

            lyric_tag = soup.select_one(".lyric")
            if lyric_tag:
                inner_html = soup.select_one(".lyric").encode_contents().decode("utf8")
                inner_html = re.sub(r"<!--.*?-->", "", inner_html).strip()
                lyric = re.sub(r"<br\s*/?>", "\n", inner_html).strip()
            else:
                lyric = ""

            genre = [s.strip() for s in meta_dict.get("장르", "").split(",") if s.strip()]
            published_date = meta_dict.get("발매일", "").replace(".", "-") or None

            return json.dumps(
                {
                    "name": name,
                    "album_name": album_name,
                    "artist_name": artist_name,
                    "cover_url": cover_url,
                    "lyric": lyric,
                    "genre": genre,
                    "published_date": published_date,
                },
                ensure_ascii=False,
            )
        except AttributeError:
            return f"Error: Not found song : {song_uid} in {vendor}"

    else:
        return f"Error: Unsupported music service vendor : {vendor}"


@mcp.tool(experimental=True)
async def music_open_song_page(
    vendor: MusicServiceVendor = Field(
        description="Music service provider. Currently only supports MELON.",
        examples=["MusicServiceVendor.MELON"],
    ),
    song_uid: SongUid = Field(
        description="Unique identifier for the song to open in browser.",
        examples=["33487916", "35338198"],
    ),
) -> str:
    """Opens the webpage for a specific song in the default web browser.

    Launches the default web browser and navigates to the song's detail page
    on the specified music streaming service.

    Returns:
        str: Message containing the opened webpage URL.

    Examples:
        >>> music_open_song_page(MusicServiceVendor.MELON, "33487916")  # Opens IU - 라일락
        >>> music_open_song_page(MusicServiceVendor.MELON, "35338198")  # Opens NewJeans - Super Shy

    Notes:
        This is an experimental feature.
        It may be modified or removed in future versions.
        The behavior depends on the system's default web browser settings.

    Raises:
        ValueError: If an unsupported music service vendor is specified
    """

    if vendor == MusicServiceVendor.MELON:
        page_url = f"https://www.melon.com/song/detail.htm?songId={song_uid}"
    else:
        return f"Error: Unsupported music service vendor : {vendor}"

    webbrowser.open_new(page_url)

    return f"Opened on {page_url}"
