
import json
import requests
import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import FormatterLoader, _TextBasedFormatter
import os


class YoutubeChaptersFinder:
    def __init__(self, youtube='https://youtube.com'):
        self.youtube = youtube

    def get_video(self, video_id: str):
        try:
            response = requests.get(f"{self.youtube}/watch?v={video_id}")
            return response.text
        except Exception as error:
            print(f"getVideo err: {error}")
   
    def get_length(self, id: str):
        html = self.get_video(id)
        script_tag_start = '"lengthSeconds":"'
        script_tag_end = '",'
        start_index = html.find(script_tag_start)
        end_index = html.find(script_tag_end, start_index)
        yt_initial_data_string = html[start_index + len(script_tag_start):end_index].strip()
        print(f"Video duration: {yt_initial_data_string}s")
        return int(yt_initial_data_string)
 
    def get_jsscript(self, html: str):
        try:
            script_tag_start = 'var ytInitialData = '
            script_tag_end = '</script>'

            start_index = html.find(script_tag_start)
            if start_index == -1:
                return None

            end_index = html.find(script_tag_end, start_index)
            if end_index == -1:
                return None

            yt_initial_data_string = html[start_index + len(script_tag_start):end_index].strip()
            if yt_initial_data_string.endswith(';'):
                return yt_initial_data_string[:-1]

            return yt_initial_data_string
        except Exception as error:
            print(f"getScript err: {error}")

    def get_chapter(self, video_id: str):
        try:
            yt_initial_data_json = json.loads(self.get_jsscript(self.get_video(video_id)))
            chapter_data = yt_initial_data_json['engagementPanels'][1]['engagementPanelSectionListRenderer']['content']['macroMarkersListRenderer']['contents']
            are_auto_generated = 'macroMarkersInfoItemRenderer' in chapter_data[0]
            filtered_contents = chapter_data[1:] if are_auto_generated else chapter_data

            chapters = []
            for chapter_item in filtered_contents:
                chapter = chapter_item['macroMarkersListItemRenderer']
                time_str = chapter['timeDescription']['simpleText']
                url = self.youtube + chapter['onTap']['commandMetadata']['webCommandMetadata']['url']
                chapters.append({
                    'title': chapter['title']['simpleText'],
                    'time': time_str,
                    'url': url
                })
            return chapters
        except Exception as error:
            print(f"getChapter err: {error}")
            return []

youtube_chapters_getter = YoutubeChaptersFinder()


def get_chapters(vid, verbose=False):
    chapters = youtube_chapters_getter.get_chapter(vid)

    def format_duration(time):
        ts = time.split(':')
        sec = int(ts[-1])
        sec = int(ts[-2])*60 + sec if len(ts) > 1 else sec
        sec = int(ts[-3])*60*60 + sec if len(ts) > 2 else sec
        return sec

    times = []
    chaps = []
    curls = []
    for chapter in chapters:
        times.append(format_duration(chapter['time']))
        chaps.append(chapter['title'])
        curls.append(chapter['url'])
        if verbose:
            print(chapter['time'], format_duration(chapter['time']), chapter['title'], chapter['url'])
    # print(chapters)
    return times, chaps, curls


def get_video_title(video_id):
    """
    Get the title of the YouTube video.
    Args:
        video_id (str): The YouTube video ID.
    Returns:
        str: The title of the video or "Unknown" if not found.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()

        matches = re.findall(r'<title>(.*?)</title>', response.text)
        return matches[0].replace(" - YouTube", "") if matches else "Unknown"
    except requests.RequestException as e:
        print(f"Error fetching video title: {e}")
        return "Unknown"


def get_video_id(youtube_url):
    """
    Extract the video ID from a YouTube URL.
    Args:
        youtube_url (str): The YouTube URL.
    Returns:
        str: The extracted video ID or None if not found.
    """
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, youtube_url)
    return match.group(1) if match else None


def download_transcript(video_id):
    """
    Download the transcript and return as a string.
    Args:
        video_id (str): The YouTube video ID.
    Returns:
        str: The transcript text or an empty string if an error occurs.
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        for transcript in transcript_list:

            # the Transcript object provides metadata properties
            print(
                transcript.video_id,
                transcript.language,
                transcript.language_code,
                # whether it has been manually created or generated by YouTube
                "Generate" if transcript.is_generated else "Manually Created",
                # whether this transcript can be translated or not
                "Translatable" if transcript.is_translatable else "Not Translatable",
                # a list of languages the transcript can be translated to
                # transcript.translation_languages,
            )

        transcript = transcript_list.find_transcript(['zh', 'zh-CN'])
        transcript_text = transcript.fetch()
        return transcript_text
    except Exception as e:
        print(f"Error downloading transcript: {e}")
        return ""


def get_script(video_id):
    if video_id:
        transcript_text = download_transcript(video_id)
        if transcript_text:
            return transcript_text
        else:
            print("Unable to download transcript.")
    else:
        print("Invalid YouTube URL.")

class ChapterFormatter(_TextBasedFormatter):
    def _format_timestamp(self, hours, mins, secs, ms):
        return "{:02d}:{:02d}:{:02d},{:03d}".format(hours, mins, secs, ms)
    
    def _format_transcript_header(self, lines):
        return ' '.join(lines)

    def _format_transcript_helper(self, i, time_text, line):
        return "{}\n{}\n{}".format(i + 1, time_text, line['text'])

    def format_transcript(self, transcript, start, end):
        lines = []
        for i, line in enumerate(transcript):
            st= line['start']
            if st < start: continue
            ed = line['start'] + line['duration']
            if ed >= end: break

            lines.append(line['text'])

        return self._format_transcript_header(lines)

def get_max_image_url(vid):
    return f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', type=str, default=None)
    parser.add_argument('-id', '--youtube_id', type=str, default=None)
    parser.add_argument('-c', '--chapter_id', type=int, default=None)
    args = parser.parse_args()

    vid = args.youtube_id if args.youtube_id else get_video_id(args.url)

    print("\n")
    print(get_video_title(vid))
    print("\n")
    print(f"Image Link: {get_max_image_url(vid)}")
    print("\n")
    
    if not args.chapter_id:
        
        times, chaps, curls = get_chapters(vid, verbose=True)
        print("\n")
        print(f"Input the index of chapter: 1-{len(chaps)-1} (chapter 0 is intro) -c $cid \n")

    else:

        cid = args.chapter_id
        times, chaps, curls = get_chapters(vid, verbose=False)
        times.append(youtube_chapters_getter.get_length(vid))
        
        script = get_script(vid)

        formatter = ChapterFormatter()
        chap = chaps[cid]
        start, end = times[cid], times[cid+1]
        ts_chap = formatter.format_transcript(script, start=start, end=end)
        print(cid+1, chap, curls[cid])
        print(ts_chap) 
    




