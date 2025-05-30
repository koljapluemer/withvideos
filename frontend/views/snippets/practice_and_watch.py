from django.views.generic import DetailView
from shared.models import Snippet
import json
from random import shuffle
import re
from frontend.interactors.enrich_snippet_vocab_with_user_progress import enrich_snippet_vocab_with_user_progress

class SnippetDetailView(DetailView):
    model = Snippet
    template_name = 'frontend/snippets/practice.html'
    context_object_name = 'snippet'

    def _deduplicate_meanings(self, meanings):
        """Deduplicate meanings based on various criteria:
        - Remove exact duplicates
        - Remove case-insensitive duplicates
        - Remove duplicates that only differ by parenthetical content
        """
        seen = set()
        unique_meanings = []
        
        for meaning in meanings:
            # Remove content in parentheses for comparison
            base_meaning = re.sub(r'\([^)]*\)', '', meaning).strip()
            # Convert to lowercase for case-insensitive comparison
            normalized = base_meaning.lower()
            
            if normalized not in seen:
                seen.add(normalized)
                unique_meanings.append(meaning)
        
        return unique_meanings

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        enriched_words = enrich_snippet_vocab_with_user_progress(self.object, user)

        # Prepare words data for Alpine.js
        words_data = []
        for word in enriched_words:
            # Get all meanings and deduplicate them
            meanings = [meaning.en for meaning in word.meanings.all()]
            unique_meanings = self._deduplicate_meanings(meanings)
            
            words_data.append({
                'id': word.id,
                'original_word': word.original_word,
                'is_new': word.is_new,
                'meanings': unique_meanings
            })
        
        # Randomize the order
        shuffle(words_data)
        
        # Add to context as JSON
        context['words_json'] = json.dumps(words_data)
        context['snippet_data'] = json.dumps({
            'youtube_id': self.object.video.youtube_id,
            'start_time': self.object.start_time,
            'end_time': self.object.end_time,
            'snippet_id': self.object.id
        })
        
        return context

class SnippetAllWordsView(SnippetDetailView):
    """View for practicing all words in a snippet, regardless of whether they're due."""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all words for this snippet
        words = self.object.words.all()
        
        # Prepare words data for Alpine.js
        words_data = []
        for word in words:
            # Get all meanings and deduplicate them
            meanings = [meaning.en for meaning in word.meanings.all()]
            unique_meanings = self._deduplicate_meanings(meanings)
            
            # Check if user has practiced this word before
            has_progress = word.vocab_practices.filter(user=self.request.user).exists()
            
            words_data.append({
                'id': word.id,
                'original_word': word.original_word,
                'is_new': not has_progress,  # Mark as new if user hasn't practiced it before
                'meanings': unique_meanings
            })
        
        # Randomize the order
        shuffle(words_data)
        
        # Add to context as JSON
        context['words_json'] = json.dumps(words_data)
        context['snippet_data'] = json.dumps({
            'youtube_id': self.object.video.youtube_id,
            'start_time': self.object.start_time,
            'end_time': self.object.end_time,
            'snippet_id': self.object.id
        })
        
        return context

class SnippetWatchView(DetailView):
    model = Snippet
    template_name = 'frontend/snippets/watch.html'
    context_object_name = 'snippet'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get next snippet
        next_snippet = self.object.video.snippets.filter(index__gt=self.object.index).first()
        
        context['snippet_data'] = json.dumps({
            'youtube_id': self.object.video.youtube_id,
            'start_time': self.object.start_time,
            'end_time': self.object.end_time,
            'next_snippet_url': next_snippet.get_absolute_url(mode='practice') if next_snippet else None
        })
        
        return context 