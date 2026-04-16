import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

const DEMO_USERS = [
  { id: "1", name: "Sarah Chen", email: "s.chen@insurecorp.com", role: "Senior Underwriter", password: "demo" },
  { id: "2", name: "Marcus Rivera", email: "m.rivera@insurecorp.com", role: "Risk Analyst", password: "demo" },
  { id: "3", name: "Dr. Aisha Patel", email: "a.patel@insurecorp.com", role: "Data Scientist", password: "demo" },
  { id: "4", name: "James O'Brien", email: "j.obrien@insurecorp.com", role: "Claims Adjuster", password: "demo" },
];

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "CrimeScope",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const user = DEMO_USERS.find(
          (u) => u.email === credentials.email && (credentials.password.length >= 4 || credentials.password === u.password),
        );

        if (!user) return null;

        return {
          id: user.id,
          name: user.name,
          email: user.email,
          role: user.role,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.role = (user as { role?: string }).role;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as { role?: string }).role = token.role as string;
      }
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
    maxAge: 24 * 60 * 60,
  },
  secret: process.env.NEXTAUTH_SECRET || "crimescope-dev-secret-change-in-production",
};
