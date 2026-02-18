import sys
import time
import threading
import signal
import pjsua2 as pj

class OutboundDialer:
    def __init__(self):
        self.ep = pj.Endpoint()
        self.call_active = False
        self.shutdown_event = threading.Event()
        self.acc = None
        self.call = None

    # ─────────────────────────────────────────────
    # Call Class
    # ─────────────────────────────────────────────
    class MyCall(pj.Call):
        def __init__(self, acc, parent, call_id=-1):
            super().__init__(acc, call_id)
            self.parent = parent

        def onCallState(self, prm):
            try:
                ci = self.getInfo()
            except AttributeError:
                ci = self.info

            print(f"Call State: {ci.stateText}")

            if ci.state == pj.InvState.DISCONNECTED:
                print("Call disconnected.")
                self.parent.call_active = False
                self.parent.shutdown_event.set()

        def onCallMediaState(self, prm):
            try:
                ci = self.getInfo()
            except AttributeError:
                ci = self.info

            for mi in ci.media:
                if (mi.type == pj.MediaType.AUDIO and
                        mi.status == pj.CallMediaStatus.ACTIVE):

                    print("Media is active")
                    
                    # CONNECT AUDIO
                    try:
                        am = pj.Endpoint.instance().audDevManager()
                    except:
                        am = pj.Endpoint.instance().audDevManager

                    try:
                        call_med = self.getAudioMedia(-1)
                    except:
                        call_med = self.audioMedia

                    try:
                        call_med.startTransmit(am.getPlaybackDevMedia())
                        am.getCaptureDevMedia().startTransmit(call_med)
                    except:
                        call_med.startTransmit(am.playbackDevMedia)
                        am.captureDevMedia.startTransmit(call_med)

    # ─────────────────────────────────────────────
    # Account Class
    # ─────────────────────────────────────────────
    class MyAccount(pj.Account):
        def onRegState(self, prm):
            print("Registration state changed")

    # ─────────────────────────────────────────────
    # Initialization
    # ─────────────────────────────────────────────
    def initialize(self):
        print("Initializing PJSIP...")
        self.ep.libCreate()

        # 1. DISABLE LOGGING (Fixes the wall of text)
        ep_cfg = pj.EpConfig()
        ep_cfg.logConfig.level = 0
        ep_cfg.logConfig.consoleLevel = 0
        
        self.ep.libInit(ep_cfg)

        # 2. Create Transports
        try:
            tcfg = pj.TransportConfig()
            tcfg.port = 5060
            self.ep.transportCreate(pj.TransportType.UDP, tcfg)
        except Exception as e:
            print(f"UDP Transport error: {e}")

        try:
            tcfg = pj.TransportConfig()
            tcfg.port = 5060
            self.ep.transportCreate(pj.TransportType.TCP, tcfg)
        except Exception as e:
            print(f"TCP Transport error: {e}")

        self.ep.libStart()
        print("PJSIP started")

        # 3. Set Null Device
        try:
            self.ep.audDevManager().setNullDev()
        except:
            self.ep.audDevManager.setNullDev()

    # ─────────────────────────────────────────────
    # Create Account
    # ─────────────────────────────────────────────
    def create_account(self):
        acc_cfg = pj.AccountConfig()
        
        # CREDENTIALS
        id_uri = "sip:08044319240@lokaviveka1m.sip.exotel.com"
        
        try:
            acc_cfg.idUri = id_uri
            acc_cfg.regConfig.registerOnAdd = False
        except:
            acc_cfg.id_uri = id_uri
            acc_cfg.reg_config.register_on_add = False

        self.acc = self.MyAccount()
        self.acc.create(acc_cfg)
        print("Account created")

    # ─────────────────────────────────────────────
    # Make Call
    # ─────────────────────────────────────────────
    def make_call(self, destination):
        self.call = self.MyCall(self.acc, self)
        call_prm = pj.CallOpParam(True)
        
        print(f"Dialing {destination}...")
        self.call.makeCall(destination, call_prm)
        self.call_active = True

    # ─────────────────────────────────────────────
    # Shutdown
    # ─────────────────────────────────────────────
    def shutdown(self):
        print("Shutting down...")
        
        # 4. PREVENT CRASH: Explicitly cleanup Python objects first
        self.call = None
        self.acc = None
        
        # Give background threads a moment to finish callbacks
        time.sleep(0.5) 

        try:
            self.ep.libDestroy()
        except Exception as e:
            pass
        print("Shutdown complete.")

# ─────────────────────────────────────────────
# Main Execution
# ─────────────────────────────────────────────
if __name__ == "__main__":
    dialer = OutboundDialer()

    def signal_handler(sig, frame):
        dialer.shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)

    try:
        dialer.initialize()
        dialer.create_account()

        dest = "sip:08697421450@pstn.in1.exotel.com:5070"
        dialer.make_call(dest)

        dialer.shutdown_event.wait()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        dialer.shutdown()