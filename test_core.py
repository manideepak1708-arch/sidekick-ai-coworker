import pytest
from core import calculate, Tools, worker_step, evaluator_step, route

def test_arithmetic():
    assert calculate('(5+3)*4')==32
    with pytest.raises(ValueError): calculate('__import__("os")')

def test_files(tmp_path):
    tools=Tools(tmp_path)
    assert tools.run('write_file',{'name':'note.txt','text':'hello'})=='Created note.txt'
    assert tools.run('read_file',{'name':'note.txt'})=='hello'
    with pytest.raises(ValueError): tools.run('read_file',{'name':'../other.txt'})
    with pytest.raises(FileExistsError): tools.run('write_file',{'name':'note.txt','text':'overwrite'})

def test_worker_and_evaluator(tmp_path):
    tools=Tools(tmp_path)
    s={'task':'2+3','rounds':0,'history':[]}
    s.update(worker_step(s,lambda *_:{'tool':'calculate','args':{'expression':'2+3'}},tools))
    assert s['history'][0]['output']=='5'
    s.update(evaluator_step(s,lambda *_: {})); assert route(s)=='worker'
    s.update(worker_step(s,lambda *_:{'answer':'5'},tools))
    s.update(evaluator_step(s,lambda *_:{'verdict':'accept'})); assert route(s)=='end'

def test_limit(): assert route({'rounds':6,'verdict':'retry'})=='end'
