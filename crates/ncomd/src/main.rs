//! `ncomd` serves one shared NCOM Arch session.
//!
//! ```text
//! ncomd                          # JSON lines on stdin/stdout
//! ncomd --listen 127.0.0.1:47820 # JSON lines over TCP, one thread per client, one shared desktop
//! ncomd --size 1920x1080 ...     # desktop size
//! ```
//! On Windows the .NET shell service hosts the same protocol on the named pipe `\\.\pipe\ncom-arch`.

use ncom_core::ipc::{serve, Session};
use ncom_core::wm::Desktop;
use std::io::{self, BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::{Arc, Mutex};
use std::thread;

fn usage() -> ! {
    eprintln!("usage: ncomd [--size WxH] [--listen ADDR]");
    std::process::exit(2)
}

fn parse_size(s: &str) -> Option<Desktop> {
    let (w, h) = s.split_once(['x', 'X'])?;
    Some(Desktop::with_size(w.trim().parse().ok()?, h.trim().parse().ok()?))
}

fn client(stream: TcpStream, session: Arc<Mutex<Session>>) -> io::Result<()> {
    let peer = stream.peer_addr().map(|a| a.to_string()).unwrap_or_default();
    let mut writer = stream.try_clone()?;
    let reader = BufReader::new(stream);
    for line in reader.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let resp = match session.lock() {
            Ok(mut s) => s.handle_json(&line),
            Err(_) => "{\"ok\":false,\"error\":\"session poisoned\"}".to_string(),
        };
        writeln!(writer, "{resp}")?;
    }
    eprintln!("ncomd: {peer} disconnected");
    Ok(())
}

fn main() {
    let mut args = std::env::args().skip(1);
    let mut desktop = Desktop::default();
    let mut listen: Option<String> = None;
    while let Some(a) = args.next() {
        match a.as_str() {
            "--size" => desktop = args.next().as_deref().and_then(parse_size).unwrap_or_else(|| usage()),
            "--listen" => listen = Some(args.next().unwrap_or_else(|| usage())),
            "--version" => {
                println!("ncomd {} (protocol {})", ncom_core::VERSION, ncom_core::PROTOCOL_VERSION);
                return;
            }
            _ => usage(),
        }
    }
    match listen {
        None => {
            let mut s = Session::new(desktop);
            let stdin = io::stdin();
            if let Err(e) = serve(&mut s, stdin.lock(), io::stdout().lock()) {
                eprintln!("ncomd: {e}");
                std::process::exit(1);
            }
        }
        Some(addr) => {
            let listener = TcpListener::bind(&addr).unwrap_or_else(|e| {
                eprintln!("ncomd: cannot listen on {addr}: {e}");
                std::process::exit(1)
            });
            eprintln!("ncomd: listening on {addr}");
            let session = Arc::new(Mutex::new(Session::new(desktop)));
            for stream in listener.incoming().flatten() {
                let s = Arc::clone(&session);
                thread::spawn(move || {
                    if let Err(e) = client(stream, s) {
                        eprintln!("ncomd: client error: {e}");
                    }
                });
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sizes() {
        assert_eq!(parse_size("1920x1080").unwrap().width, 1920.0);
        assert!(parse_size("wide").is_none());
    }

    #[test]
    fn tcp_round_trip() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        let session = Arc::new(Mutex::new(Session::default()));
        let s = Arc::clone(&session);
        thread::spawn(move || {
            let (stream, _) = listener.accept().unwrap();
            let _ = client(stream, s);
        });
        let mut c = TcpStream::connect(addr).unwrap();
        writeln!(c, "{{\"cmd\":\"hello\"}}").unwrap();
        let mut line = String::new();
        BufReader::new(c.try_clone().unwrap()).read_line(&mut line).unwrap();
        assert!(line.starts_with("{\"ok\":true"), "{line}");
    }
}
