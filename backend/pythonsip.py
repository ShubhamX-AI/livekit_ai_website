import sys
import time
import threading
import signal
import pjsua2 as pj

class OutboundDialer:
    def __init__(self):
        # We create the endpoint wrapper, but don't init the library yet
        self.ep = pj.Endpoint()
        self.call_active = False
        self.shutdown_event = threading.Event()
        self.acc = None
        self.call = None

    # ─────────────────────────────────────────────
    # Call Class (Nested for access to parent)
    # ─────────────────────────────────────────────
    class MyCall(pj.Call):
        def __init__(self, acc, parent, call_id=-1):
            super().__init__(acc, call_id)
            self.parent = parent

        def onCallState(self, prm):
            # Defensive coding for getInfo vs info property
            try:
                ci = self.getInfo()
            except AttributeError:
                ci = self.info

            print(f"Call state: {ci.stateText}")

            if ci.state == pj.InvState.DISCONNECTED:
                print("Call disconnected")
                self.parent.call_active = False
                # Signal the main thread to stop waiting
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

                    # 1. Get Audio Device Manager (Handle Callable vs Property)
                    try:
                        am = pj.Endpoint.instance().audDevManager()
                    except (TypeError, AttributeError):
                        am = pj.Endpoint.instance().audDevManager

                    # 2. Get Audio Media for this call
                    try:
                        call_med = self.getAudioMedia(-1)
                    except AttributeError:
                        call_med = self.audioMedia

                    # 3. Connect Audio (Handle Method vs Property)
                    try:
                        # Try method style (Standard)
                        call_med.startTransmit(am.getPlaybackDevMedia())
                        am.getCaptureDevMedia().startTransmit(call_med)
                    except (TypeError, AttributeError):
                        # Try property style (Your version)
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
        ep_cfg = pj.EpConfig()
        self.ep.libInit(ep_cfg)

        # Create UDP transport
        try:
            udp_cfg = pj.TransportConfig()
            udp_cfg.port = 5060
            self.ep.transportCreate(pj.TransportType.UDP, udp_cfg)
        except Exception as e:
            print(f"Warning: UDP Transport failed: {e}")

        # Create TCP transport
        try:
            tcp_cfg = pj.TransportConfig()
            tcp_cfg.port = 5060
            self.ep.transportCreate(pj.TransportType.TCP, tcp_cfg)
        except Exception as e:
            print(f"Warning: TCP Transport failed: {e}")

        self.ep.libStart()
        print("PJSIP started")

        # Set Null Device (Fixes your specific TypeError)
        try:
            self.ep.audDevManager().setNullDev()
        except (TypeError, AttributeError):
            self.ep.audDevManager.setNullDev()

    # ─────────────────────────────────────────────
    # Create Account
    # ─────────────────────────────────────────────
    def create_account(self):
        acc_cfg = pj.AccountConfig()

        # Handle Snake_case vs CamelCase
        try:
            acc_cfg.idUri = "sip:08044319240@lokaviveka1m.sip.exotel.com"
            acc_cfg.regConfig.registerOnAdd = False
        except AttributeError:
            acc_cfg.id_uri = "sip:08044319240@lokaviveka1m.sip.exotel.com"
            acc_cfg.reg_config.register_on_add = False

        self.acc = self.MyAccount()
        self.acc.create(acc_cfg)
        print("Account created")

    # ─────────────────────────────────────────────
    # Make Call
    # ─────────────────────────────────────────────
    def make_call(self, destination):
        if not self.acc:
            print("Error: Account not created yet.")
            return

        # Pass 'self' (the OutboundDialer instance) as parent
        self.call = self.MyCall(self.acc, self)
        
        call_prm = pj.CallOpParam(True)

        print(f"Dialing {destination}...")
        self.call.makeCall(destination, call_prm)
        self.call_active = True

    # ─────────────────────────────────────────────
    # Shutdown
    # ─────────────────────────────────────────────
    def shutdown(self):
        print("Shutting down PJSIP...")
        try:
            self.ep.libDestroy()
        except Exception as e:
            print(f"Error during destroy (might be already destroyed): {e}")
        print("Shutdown complete.")


# ─────────────────────────────────────────────
# Signal Handler
# ─────────────────────────────────────────────
def signal_handler(sig, frame):
    print("\nInterrupt received. Exiting...")
    if 'dialer' in globals():
        dialer.shutdown_event.set()

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    dialer = OutboundDialer()
    signal.signal(signal.SIGINT, signal_handler)

    try:
        dialer.initialize()
        dialer.create_account()

        destination = "sip:08697421450@pstn.in1.exotel.com:5070"
        dialer.make_call(destination)

        # Block here until call ends or Ctrl+C
        dialer.shutdown_event.wait()

    except Exception as e:
        print(f"Runtime Error: {e}")

    finally:
        dialer.shutdown()
        sys.exit(0)