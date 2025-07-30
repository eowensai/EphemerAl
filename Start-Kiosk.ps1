$wslIP = (wsl -- hostname -I).Split()[0]
netsh interface portproxy delete v4tov4 listenport=8501 listenaddress=0.0.0.0 2>$null
netsh interface portproxy add v4tov4 listenport=8501 listenaddress=0.0.0.0 connectport=8501 connectaddress=$wslIP
wsl -- sleep infinity
