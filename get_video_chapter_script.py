from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.pin import *

import importlib  
from youtube_chapter_transcript import *

def main():
    form = input_group('', [
            input(name='url', placeholder='Youtube URL', type=URL),
            input(name='cid', 
                placeholder='chapter id (if you do not know how many chapters this need, leave it empty to see the number)', 
                type=NUMBER,)
            # actions(name='cmd', buttons=['Send', 'Multi-line Input', 'Save Chat'])
        ])
    put_scrollable(put_scope('result-box'), height=800, keep_bottom=True)
    
    url = form['url']
    cid = form['cid']
    vid = get_video_id(form['url'])

    video_title = get_video_title(vid)
    video_cover_image_url = get_max_image_url(vid)
    put_markdown(f"Video Title: {video_title}", sanitize=True, scope='result-box')
    put_markdown(f"Video Cover Image: {video_cover_image_url}", sanitize=True, scope='result-box')
    

    if not cid:
        
        times_orig, times, chaps, curls = get_chapters(vid, verbose=False)
        put_markdown("---", sanitize=True, scope='result-box')

        for i in range(len(chaps)):
            put_markdown("{}, {}, {}, {}".format(
                times_orig[i], times[i], chaps[i], curls[i],
                ), sanitize=True, scope='result-box')

        put_markdown("---", sanitize=True, scope='result-box')
        put_markdown(f"There are {len(chaps)-1} chapters in total (chapter 0 is intro)",
            sanitize=True, scope='result-box')

    else:
        times_orig, times, chaps, curls = get_chapters(vid, verbose=False)
        put_markdown("---", sanitize=True, scope='result-box')
        times.append(youtube_chapters_getter.get_length(vid))
        
        script = get_script(vid)

        formatter = ChapterFormatter()
        chap = chaps[cid]
        start, end = times[cid], times[cid+1]
        ts_chap = formatter.format_transcript(script, start=start, end=end)

        put_markdown("---", sanitize=True, scope='result-box')
        put_markdown("{}, {}, {}".format(
                cid, chap, curls[cid]
                ), sanitize=True, scope='result-box')
        put_markdown("---", sanitize=True, scope='result-box')
        put_markdown(ts_chap, sanitize=True, scope='result-box')

    

if __name__ == '__main__':
    start_server(main, port=3001)