import os
import subprocess
import time
from datetime import datetime

import pytest

from client_test import run_client_many
from tests.test_langchain_units import have_openai_key
from tests.utils import wrap_test_forked


@wrap_test_forked
def test_gradio_inference_server(prompt='Who are you?', stream_output=False, max_new_tokens=256,
                                 base_model='h2oai/h2ogpt-oig-oasst1-512-6_9b', prompt_type='human_bot',
                                 langchain_mode='Disabled', user_path=None,
                                 visible_langchain_modes=['UserData', 'MyData'],
                                 reverse_docs=True):
    main_kwargs = dict(base_model=base_model, prompt_type=prompt_type, chat=True,
                       stream_output=stream_output, gradio=True, num_beams=1, block_gradio_exit=False,
                       max_new_tokens=max_new_tokens,
                       langchain_mode=langchain_mode, user_path=user_path,
                       visible_langchain_modes=visible_langchain_modes,
                       reverse_docs=reverse_docs)

    # inference server
    inf_port = os.environ['GRADIO_SERVER_PORT'] = "7860"
    from generate import main
    main(**main_kwargs)

    # server that consumes inference server
    client_port = os.environ['GRADIO_SERVER_PORT'] = "7861"
    from generate import main
    main(**main_kwargs, inference_server='http://127.0.0.1:%s' % inf_port)

    # client test to server that only consumes inference server
    from client_test import run_client_chat
    os.environ['HOST'] = "http://127.0.0.1:%s" % client_port
    res_dict, client = run_client_chat(prompt=prompt, prompt_type=prompt_type, stream_output=stream_output,
                                       max_new_tokens=max_new_tokens, langchain_mode=langchain_mode)
    assert res_dict['prompt'] == prompt
    assert res_dict['iinput'] == ''

    # will use HOST from above
    ret1, ret2, ret3, ret4, ret5, ret6, ret7 = run_client_many()
    assert 'h2oGPT' in ret1['response']
    assert 'Birds' in ret2['response']
    assert 'Birds' in ret3['response']
    assert 'h2oGPT' in ret4['response']
    assert 'h2oGPT' in ret5['response']
    assert 'h2oGPT' in ret6['response']
    assert 'h2oGPT' in ret7['response']
    print("DONE", flush=True)


def run_docker(inf_port):
    datetime_str = str(datetime.now()).replace(" ", "_").replace(":", "_")
    msg = "Starting HF inference %s..." % datetime_str
    print(msg, flush=True)
    home_dir = os.path.expanduser('~')
    data_dir = '%s/.cache/huggingface/hub/' % home_dir
    cmd = ["docker"] + ['run',
                        '--gpus', 'device=0',
                        '--shm-size', '1g',
                        '-e', 'TRANSFORMERS_CACHE="/.cache/"',
                        '-p', '%s:80' % inf_port,
                        '-v', '%s/.cache:/.cache/' % home_dir,
                        '-v', '%s:/data' % data_dir,
                        'ghcr.io/huggingface/text-generation-inference:0.8.2',
                        '--model-id', 'h2oai/h2ogpt-gm-oasst1-en-2048-falcon-7b-v2',
                        '--max-input-length', '2048',
                        '--max-total-tokens', '3072',
                        ]
    print(cmd, flush=True)
    p = subprocess.Popen(cmd,
                         stdout=None, stderr=subprocess.STDOUT,
                         )
    print("Done starting autoviz server", flush=True)
    return p.pid


@wrap_test_forked
def test_hf_inference_server(prompt='Who are you?', stream_output=False, max_new_tokens=256,
                             base_model='h2oai/h2ogpt-oig-oasst1-512-6_9b', prompt_type='human_bot',
                             langchain_mode='Disabled', user_path=None,
                             visible_langchain_modes=['UserData', 'MyData'],
                             reverse_docs=True):
    main_kwargs = dict(base_model=base_model, prompt_type=prompt_type, chat=True,
                       stream_output=stream_output, gradio=True, num_beams=1, block_gradio_exit=False,
                       max_new_tokens=max_new_tokens,
                       langchain_mode=langchain_mode, user_path=user_path,
                       visible_langchain_modes=visible_langchain_modes,
                       reverse_docs=reverse_docs)

    # HF inference server
    inf_port = "6112"
    inf_pid = run_docker(inf_port=inf_port)
    time.sleep(30)

    try:
        # server that consumes inference server
        client_port = os.environ['GRADIO_SERVER_PORT'] = "7861"
        from generate import main
        main(**main_kwargs, inference_server='http://127.0.0.1:%s' % inf_port)

        # client test to server that only consumes inference server
        from client_test import run_client_chat
        os.environ['HOST'] = "http://127.0.0.1:%s" % client_port
        res_dict, client = run_client_chat(prompt=prompt, prompt_type=prompt_type, stream_output=stream_output,
                                           max_new_tokens=max_new_tokens, langchain_mode=langchain_mode)
        assert res_dict['prompt'] == prompt
        assert res_dict['iinput'] == ''

        # will use HOST from above
        ret1, ret2, ret3, ret4, ret5, ret6, ret7 = run_client_many()
        # FIXME: not h2oGPT response
        # AssertionError: assert 'h2oGPT' in 'I am a language model trained to respond to your questions and provide information.'
        assert 'h2oGPT' in ret1['response']
        assert 'Birds' in ret2['response']
        assert 'Birds' in ret3['response']
        assert 'h2oGPT' in ret4['response']
        assert 'h2oGPT' in ret5['response']
        assert 'h2oGPT' in ret6['response']
        assert 'h2oGPT' in ret7['response']
        print("DONE", flush=True)
    finally:
        # take down docker server
        import signal
        os.kill(inf_pid, signal.SIGTERM)
        os.kill(inf_pid, signal.SIGKILL)

        os.system("docker ps | grep text-generation-inference | awk '{print $1}' | xargs docker stop ")


@pytest.mark.skipif(not have_openai_key, reason="requires OpenAI key to run")
def test_openai_inference_server(prompt='Who are you?', stream_output=False, max_new_tokens=256,
                                 base_model='gpt-3.5-turbo',
                                 langchain_mode='Disabled', user_path=None,
                                 visible_langchain_modes=['UserData', 'MyData'],
                                 reverse_docs=True):
    main_kwargs = dict(base_model=base_model, chat=True,
                       stream_output=stream_output, gradio=True, num_beams=1, block_gradio_exit=False,
                       max_new_tokens=max_new_tokens,
                       langchain_mode=langchain_mode, user_path=user_path,
                       visible_langchain_modes=visible_langchain_modes,
                       reverse_docs=reverse_docs)

    # server that consumes inference server
    client_port = os.environ['GRADIO_SERVER_PORT'] = "7861"
    from generate import main
    main(**main_kwargs, inference_server='openai_chat')

    # client test to server that only consumes inference server
    from client_test import run_client_chat
    os.environ['HOST'] = "http://127.0.0.1:%s" % client_port
    res_dict, client = run_client_chat(prompt=prompt, prompt_type='openai_chat', stream_output=stream_output,
                                       max_new_tokens=max_new_tokens, langchain_mode=langchain_mode)
    assert res_dict['prompt'] == prompt
    assert res_dict['iinput'] == ''

    # will use HOST from above
    ret1, ret2, ret3, ret4, ret5, ret6, ret7 = run_client_many()
    assert 'I am an AI language model designed to assist' in ret1['response']
    assert 'I am an AI language model designed to assist' in ret2['response']
    assert 'Once upon a time, in a far-off land,' in ret3['response']
    assert 'Once upon a time, in a far-off land,' in ret4['response']
    assert 'I am an AI language model' in ret5['response']
    assert 'I am an AI language model' in ret6['response']
    assert 'I am an AI language model' in ret7['response']
    print("DONE", flush=True)