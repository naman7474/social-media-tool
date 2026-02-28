export default function WaitlistPage() {
    return (
        <main className="min-h-screen bg-wabi-bg text-wabi-text px-6 py-16">
            <div className="max-w-2xl mx-auto">
                <h1 className="font-serif text-4xl mb-4">Join the Waitlist</h1>
                <p className="text-wabi-text/70 mb-8">
                    Early access is currently invite-only for managed pilot brands.
                    Contact us with your brand name, Instagram handle, and posting goals.
                </p>
                <a
                    href="mailto:hello@example.com?subject=Waitlist%20Request"
                    className="inline-block bg-wabi-text text-wabi-bg px-6 py-3 rounded-lg"
                >
                    Email for Access
                </a>
            </div>
        </main>
    );
}
